import logging
import os
import sys
import tempfile
import time
import threading
from collections import OrderedDict

import io
import concurrent.futures
from googleapiclient.http import MediaIoBaseDownload
from dotenv import load_dotenv
from pymongo import MongoClient  # Added
from datetime import datetime  # Added

load_dotenv()

current_file_dir = os.path.dirname(os.path.abspath(__file__))
project_root_dir = os.path.abspath(os.path.join(current_file_dir, ".."))
power_ocr_module_path = os.path.join(project_root_dir, "power-ocr")

if power_ocr_module_path not in sys.path:
    sys.path.insert(0, power_ocr_module_path)

try:
    from PdfProcessor.PdfTranscriptionToolGemini import PdfTranscriptionToolGemini
    from VideoProcessor.VideoTranscriptionTool import transcribe_video
except ImportError as e:
    logging.getLogger(__name__).error(
        f"Failed to import OCR tools: {e}. Ensure power-ocr directory is structured correctly and contains __init__.py files if necessary."
    )

# --- Constants ---
VIDEO_MIME_TYPES = [
    "video/mp4",
    "video/mpeg",
    "video/quicktime",
    "video/x-msvideo",  # AVI
    "video/x-matroska",  # MKV
    "video/webm",
    "video/x-flv",
    "video/3gpp",
    "video/x-ms-wmv",
]

# --- Thread Pool Executor for Background Tasks ---
# Using a dynamic number of workers up to the number of CPU cores, with a minimum of 1
# Adjust max_workers as needed based on application load and resources
executor = concurrent.futures.ThreadPoolExecutor(max_workers=(os.cpu_count() or 1) * 2)

# --- Logging Setup ---
logger = logging.getLogger(__name__)

# --- MongoDB Client Setup ---
MONGO_URI = os.environ.get("MONGO_URI")
MONGO_DB_NAME = os.environ.get("MONGO_DB_NAME")
mongo_client = None
db = None

if MONGO_URI and MONGO_DB_NAME:
    try:
        mongo_client = MongoClient(MONGO_URI)
        db = mongo_client[MONGO_DB_NAME]
        logger.info(f"Successfully connected to MongoDB: {MONGO_DB_NAME}")
    except Exception as e:
        logger.error(f"Failed to connect to MongoDB: {e}", exc_info=True)
        mongo_client = None
        db = None
else:
    logger.warning(
        "MongoDB URI or DB Name not configured. Database operations will be skipped."
    )


# --- In-Memory Cache for Recently Processed Files ---
# This helps prevent duplicate processing from multiple Drive notifications
class TTLCache:
    def __init__(self, ttl_seconds=300, max_size=1000):
        """
        Time-based cache with expiration

        Args:
            ttl_seconds: Time in seconds items remain valid in cache (default: 5 minutes)
            max_size: Maximum number of items to store in cache
        """
        self.ttl_seconds = ttl_seconds
        self.max_size = max_size
        self.cache = OrderedDict()  # {key: (value, timestamp)}
        self.lock = threading.RLock()

        # Start a cleaning thread
        self.cleanup_thread = threading.Thread(target=self._cleanup_loop, daemon=True)
        self.cleanup_thread.start()
        logger.info(
            f"In-memory TTL cache initialized (TTL: {ttl_seconds}s, Max size: {max_size} items)"
        )

    def set(self, key, value=True):
        """Add an item to the cache with current timestamp"""
        with self.lock:
            self.cache[key] = (value, time.time())

            # If cache exceeds max size, remove oldest items
            if len(self.cache) > self.max_size:
                # Remove 10% of the oldest entries
                to_remove = max(1, int(self.max_size * 0.1))
                for _ in range(to_remove):
                    if self.cache:
                        self.cache.popitem(last=False)

    def get(self, key, default=None):
        """Get an item from cache if it exists and hasn't expired"""
        with self.lock:
            if key not in self.cache:
                return default

            value, timestamp = self.cache[key]
            if time.time() - timestamp > self.ttl_seconds:
                # Expired item, remove it
                del self.cache[key]
                return default

            # Move to the end (most recently used)
            self.cache.move_to_end(key)
            return value

    def _cleanup_loop(self):
        """Periodically clean up expired items"""
        while True:
            time.sleep(60)  # Check every minute
            try:
                self._cleanup()
            except Exception as e:
                logger.error(f"Error during cache cleanup: {e}")

    def _cleanup(self):
        """Remove expired items from cache"""
        with self.lock:
            current_time = time.time()
            keys_to_delete = []

            for key, (value, timestamp) in self.cache.items():
                if current_time - timestamp > self.ttl_seconds:
                    keys_to_delete.append(key)

            for key in keys_to_delete:
                del self.cache[key]

            if keys_to_delete:
                logger.debug(
                    f"Cleaned up {len(keys_to_delete)} expired items from cache"
                )


# Create the cache with a 5-minute TTL
processing_cache = TTLCache(ttl_seconds=300)


def _download_file_from_drive(drive_service, file_id, download_path, dl_logger):
    try:
        dl_logger.info(f"Starting download for file ID: {file_id} to {download_path}")
        request = drive_service.files().get_media(fileId=file_id)
        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while not done:
            status, done = downloader.next_chunk()
            dl_logger.debug(
                f"Download progress for {file_id}: {int(status.progress() * 100)}%"
            )

        with open(download_path, "wb") as f:
            f.write(fh.getvalue())
        dl_logger.info(f"File ID: {file_id} downloaded successfully to {download_path}")
        return True
    except Exception as e:
        dl_logger.error(f"Failed to download file ID {file_id}: {e}", exc_info=True)
        return False


def _store_result_in_db(file_id, file_name, ocr_result_text):
    """
    Stores OCR results in MongoDB, using upsert to avoid duplicates based on google_document_id.
    """
    if db is None:  # Corrected check for db connection
        logger.error("MongoDB not available. Skipping storing OCR result.")
        return

    try:
        collection_name = "processed_files"  # Or your desired collection name
        collection = db[collection_name]

        # Data to be set or updated
        current_time = datetime.utcnow()
        set_payload = {
            "file_name": file_name,
            "content": ocr_result_text,
            "processed_at": current_time,  # Timestamp of the latest processing
        }

        # Data to be set only on insert (when the document is first created)
        set_on_insert_payload = {
            "google_document_id": file_id,  # Ensure this is part of the document
            "first_processed_at": current_time,  # Timestamp of the first processing
        }

        # Perform an upsert operation
        # If a document with 'google_document_id' exists, it's updated.
        # Otherwise, a new document is inserted.
        update_result = collection.update_one(
            {"google_document_id": file_id},  # Query to find the document
            {"$set": set_payload, "$setOnInsert": set_on_insert_payload},
            upsert=True,  # Enable upsert
        )

        if update_result.upserted_id:
            logger.info(
                f"Successfully inserted OCR result for file ID: {file_id}, Name: {file_name} in MongoDB. Document ID: {update_result.upserted_id}"
            )
        elif update_result.modified_count > 0:
            logger.info(
                f"Successfully updated OCR result for file ID: {file_id}, Name: {file_name} in MongoDB."
            )
        elif update_result.matched_count > 0:
            logger.info(
                f"Processed OCR result for file ID: {file_id}, Name: {file_name}. Document existed, content was identical or no change made."
            )
        else:
            # This case should ideally not be reached if upsert is true and there's no error.
            logger.warning(
                f"OCR result processing for file ID: {file_id}, Name: {file_name} resulted in no change and no upsert/match. Result: {update_result.raw_result}"
            )

    except Exception as e:
        logger.error(
            f"Failed to store/update OCR result for file ID {file_id} in MongoDB: {e}",
            exc_info=True,
        )


def _process_file_task(
    file_metadata, user_google_id, folder_id, drive_service, task_logger
):
    """
    Background task to download, OCR, and store results for a file.
    """
    file_id = file_metadata.get("id")
    file_name = file_metadata.get("name")
    mime_type = file_metadata.get("mimeType")

    task_logger.info(
        f"Background task started for File ID: {file_id}, Name: {file_name}, MIME Type: {mime_type}, Watched Folder Context: {folder_id}"
    )

    # Check if the file has already been processed
    if db is not None:
        try:
            collection_name = (
                "processed_files"  # Same collection name as in _store_result_in_db
            )
            collection = db[collection_name]
            existing_document = collection.find_one({"google_document_id": file_id})
            if existing_document:
                task_logger.info(
                    f"File ID: {file_id}, Name: {file_name} already processed and stored in DB. Skipping."
                )
                return  # Exit the task if already processed
        except Exception as e:
            task_logger.error(
                f"Error checking MongoDB for existing file ID {file_id}: {e}",
                exc_info=True,
            )
            # Decide if we should proceed or not. For now, let's proceed if DB check fails,
            # as it's better to re-process than to miss a file due to a temporary DB issue.
            # However, this could lead to duplicates if the DB issue persists during the store phase.

    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            downloaded_file_path = os.path.join(
                temp_dir, file_name if file_name else "downloaded_file"
            )

            if not _download_file_from_drive(
                drive_service, file_id, downloaded_file_path, task_logger
            ):
                task_logger.error(
                    f"Halting processing for file ID {file_id} due to download failure."
                )
                return

            ocr_text = None
            if mime_type == "application/pdf":
                task_logger.info(f"Processing PDF file: {file_name}")
                try:
                    pdf_api_endpoint = os.environ.get("PDF_OCR_API_ENDPOINT")
                    pdf_model_name = os.environ.get("PDF_OCR_MODEL_NAME")
                    pdf_api_key = os.environ.get("PDF_OCR_API_KEY")

                    if not all([pdf_api_endpoint, pdf_model_name, pdf_api_key]):
                        task_logger.error(
                            f"Missing one or more PDF OCR environment variables (PDF_OCR_API_ENDPOINT, PDF_OCR_MODEL_NAME, PDF_OCR_API_KEY) for {file_name}. Skipping PDF OCR."
                        )
                        ocr_text = "Error: PDF OCR configuration missing."
                    else:
                        tool = PdfTranscriptionToolGemini(
                            api_endpoint=pdf_api_endpoint,
                            model_name=pdf_model_name,
                            api_key=pdf_api_key,
                        )
                        ocr_text = tool.process(downloaded_file_path)
                        task_logger.info(f"PDF OCR successful for {file_name}.")
                except Exception as e:
                    task_logger.error(
                        f"Error during PDF OCR for {file_name}: {e}", exc_info=True
                    )
                    ocr_text = f"Error processing PDF: {e}"

            elif mime_type in VIDEO_MIME_TYPES:
                task_logger.info(f"Processing video file: {file_name}")
                try:
                    video_api_key = os.environ.get("VIDEO_OCR_API_KEY")
                    video_api_url = os.environ.get("VIDEO_OCR_API_URL")
                    # Use environment variable or default to "whisper-large-v3"
                    video_model_name = (
                        os.environ.get("VIDEO_OCR_MODEL_NAME") or "whisper-large-v3"
                    )

                    if not all(
                        [video_api_key, video_api_url]
                    ):  # video_model_name is now guaranteed
                        task_logger.error(
                            f"Missing one or more Video transcription environment variables (VIDEO_OCR_API_KEY, VIDEO_OCR_API_URL) for {file_name}. VIDEO_OCR_MODEL_NAME defaults to '{video_model_name}' if not set. Skipping video transcription."
                        )
                        ocr_text = "Error: Video transcription configuration missing essential API key or URL."
                    else:
                        params = {
                            "video_path": downloaded_file_path,
                            "api_key": video_api_key,
                            "api_url": video_api_url,
                            "model": video_model_name,
                            "output_format": "plain",
                        }
                        ocr_response = transcribe_video(params)
                        if ocr_response.get("status") == "success":
                            ocr_text = ocr_response.get("transcription", "")
                            task_logger.info(
                                f"Video transcription successful for {file_name}."
                            )
                        else:
                            error_msg = ocr_response.get(
                                "error", "Unknown video transcription error"
                            )
                            task_logger.error(
                                f"Video transcription failed for {file_name}: {error_msg}"
                            )
                            ocr_text = f"Error processing video: {error_msg}"
                except Exception as e:
                    task_logger.error(
                        f"Error during video transcription for {file_name}: {e}",
                        exc_info=True,
                    )
                    ocr_text = f"Error processing video: {e}"
            else:
                task_logger.info(
                    f"File type {mime_type} for {file_name} is not supported for OCR. Skipping."
                )
                return

            if ocr_text is not None:
                _store_result_in_db(file_id, file_name, ocr_text)
            else:
                task_logger.warning(
                    f"No OCR text generated for {file_name} (ID: {file_id}). Nothing to store."
                )

    except ValueError as ve:  # Catch missing env vars specifically
        task_logger.error(f"Configuration error for file ID {file_id}: {ve}")
    except Exception as e:
        task_logger.error(
            f"Unhandled error in background task for file ID {file_id}, Name: {file_name}: {e}",
            exc_info=True,
        )
    finally:
        task_logger.info(
            f"Background task finished for File ID: {file_id}, Name: {file_name}"
        )


def process_new_file(
    file_metadata, user_google_id, folder_id, drive_service=None
):  # folder_id is the main watched folder
    item_id = file_metadata.get("id")
    item_name = file_metadata.get("name")
    mime_type = file_metadata.get("mimeType")

    logger.info(
        f"Processing trigger for item: ID {item_id}, Name: {item_name}, MIME: {mime_type}, Watched Folder Context: {folder_id}"
    )

    if not drive_service:
        logger.error(
            f"Drive service not available. Cannot process item: {item_name} (ID: {item_id})"
        )
        return

    # Early check to avoid submitting already processed files
    # The definitive check still exists in _process_file_task as a safeguard.
    if db is not None and item_id:  # Ensure db is connected and item_id is not None
        try:
            processed_files_collection = db["processed_files"]
            if processed_files_collection.find_one({"google_document_id": item_id}):
                logger.info(
                    f"File ID: {item_id}, Name: {item_name} already processed (checked in process_new_file). Skipping submission to background task."
                )
                return  # Skip submitting to executor
        except Exception as e:
            logger.error(
                f"Error during initial DB check for file ID {item_id} in process_new_file: {e}. Proceeding to submit task for definitive check.",
                exc_info=True,
            )
            # If DB check fails here, let _process_file_task handle the definitive check later.

    # Check in-memory cache to prevent duplicate processing
    if processing_cache.get(item_id):
        logger.info(
            f"File ID: {item_id}, Name: {item_name} is already being processed (checked in in-memory cache). Skipping submission to background task."
        )
        return  # Skip submitting to executor

    if mime_type == "application/pdf" or mime_type in VIDEO_MIME_TYPES:
        logger.info(
            f"Item {item_name} (ID: {item_id}, Type: {mime_type}) is a processable file. Submitting to background task."
        )
        try:
            # Add to in-memory cache to prevent duplicate processing
            processing_cache.set(item_id)

            # _process_file_task already checks if the file (by its ID) is in the database.
            executor.submit(
                _process_file_task,
                file_metadata,  # Metadata of the PDF/video file
                user_google_id,
                folder_id,  # ID of the main folder being watched by the webhook (passed for context)
                drive_service,
                logger,  # Main logger from file_processor.py
            )
        except Exception as e:
            logger.error(f"Error submitting task to executor for {item_name}: {e}")
    else:
        logger.info(
            f"Item {item_name} (ID: {item_id}, Type: {mime_type}) is not a PDF or video. Skipping processing."
        )

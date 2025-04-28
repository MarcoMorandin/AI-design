# app/services/task_manager.py
import logging
import uuid
import datetime
from pathlib import Path
from typing import Optional

from app.db.mongodb import get_task_collection
from app.models.task import TaskStatus, TaskDocument
from app.core.config import settings
from app.utils import file_handler # Import download and cleanup
from app.services import video_processing, llm # Import processing steps
from pydantic import HttpUrl
from bson import ObjectId # Needed if not using Pydantic alias correctly

logger = logging.getLogger(__name__)

async def create_task_in_db(video_url: HttpUrl) -> uuid.UUID:
    """Creates a new task record in MongoDB and returns its task_id."""
    task_id = uuid.uuid4()
    task_doc = TaskDocument(
        task_id=task_id,
        video_url=video_url,
        status=TaskStatus.PENDING,
        created_at=datetime.datetime.now(datetime.timezone.utc), # Use timezone-aware UTC
        updated_at=datetime.datetime.now(datetime.timezone.utc)
    )
    collection = get_task_collection()
    # Pydantic v2+ export suitable for mongo
    
    insert_data = task_doc.model_dump(
        mode='json',
        by_alias=True,
        exclude={'id'}
    )
    
    insert_data['_id'] = task_id # Explicitly set _id as the task_id UUID for easier querying
    
    await collection.insert_one(insert_data)
    logger.info(f"Created task {task_id} for URL {video_url} in DB.")
    return task_id

async def update_task_status(task_id: uuid.UUID, status: TaskStatus, error_message: Optional[str] = None):
    """Updates the status and updated_at time of a task in MongoDB."""
    collection = get_task_collection()
    update_fields = {
        "status": status.value,
        "updated_at": datetime.datetime.now(datetime.timezone.utc),
    }
    if error_message:
        update_fields["error_message"] = error_message

    result = await collection.update_one(
        {"_id": task_id}, # Query by _id which we set to task_id
        {"$set": update_fields}
    )
    if result.matched_count == 0:
        logger.error(f"Task ID {task_id} not found in DB for status update.")
    else:
         logger.info(f"Updated task {task_id} status to {status.value}" + (f" with error: {error_message}" if error_message else ""))


async def update_task_result(task_id: uuid.UUID, essay_content: str):
    """Updates the task with the final essay and sets status to DONE."""
    collection = get_task_collection()
    update_fields = {
        "essay": essay_content,
        "status": TaskStatus.DONE.value,
        "updated_at": datetime.datetime.now(datetime.timezone.utc),
        "error_message": None # Clear any previous potential errors if we somehow got here
    }
    result = await collection.update_one(
        {"_id": task_id},
        {"$set": update_fields}
    )
    if result.matched_count == 0:
         logger.error(f"Task ID {task_id} not found in DB for result update.")
    else:
        logger.info(f"Stored essay result for task {task_id} and marked as DONE.")


async def get_task_from_db(task_id: uuid.UUID) -> Optional[dict]:
     """Retrieves a task document from MongoDB by task_id."""
     collection = get_task_collection()
     task_data = await collection.find_one({"_id": task_id})
     return task_data # Returns dict or None

# --- The Main Background Processing Function ---
async def process_video_essay_task(task_id: uuid.UUID, video_url: HttpUrl):
    """The background task performing the full video-to-essay pipeline."""
    logger.info(f"[Task:{task_id}] Starting background processing for URL: {video_url}")
    temp_video_path: Optional[Path] = None
    temp_audio_path: Optional[Path] = None

    try:
        # 1. Update status: DOWNLOADING
        await update_task_status(task_id, TaskStatus.DOWNLOADING)
        temp_video_path = await file_handler.download_video_from_url(video_url)
        temp_audio_path = file_handler.get_temp_audio_path(temp_video_path)
        logger.info(f"[Task:{task_id}] Video downloaded to {temp_video_path}")

        # 2. Update status: EXTRACTING_AUDIO
        await update_task_status(task_id, TaskStatus.EXTRACTING)
        if not await video_processing.extract_audio(temp_video_path, temp_audio_path):
            # video_processing service logs the specific error
            raise ValueError("Audio extraction failed.") # Raise specific error to be caught below
        logger.info(f"[Task:{task_id}] Audio extracted to {temp_audio_path}")

        # 3. Update status: TRANSCRIBING
        await update_task_status(task_id, TaskStatus.TRANSCRIBING)
        transcript = await video_processing.transcribe_audio(temp_audio_path)
        if transcript is None:
             raise ValueError("Audio transcription failed.")
        if not transcript.strip():
             raise ValueError("Transcription resulted in empty text.")
        logger.info(f"[Task:{task_id}] Transcription successful.")

        # 4. Update status: GENERATING_ESSAY
        await update_task_status(task_id, TaskStatus.GENERATING)
        essay = await llm.generate_essay_from_transcript(transcript)
        # llm service raises ConnectionError, ValueError, RuntimeError on failure
        logger.info(f"[Task:{task_id}] Essay generation successful.")

        # 5. Update status: DONE and store result
        await update_task_result(task_id, essay)
        logger.info(f"[Task:{task_id}] Task completed successfully.")

    except Exception as e:
        # Catch any exception during the process
        error_msg = f"Task failed: {type(e).__name__} - {str(e)}"
        logger.error(f"[Task:{task_id}] {error_msg}", exc_info=True)
        # Update status to FAILED with error message
        await update_task_status(task_id, TaskStatus.FAILED, error_message=error_msg)

    finally:
        # 6. Cleanup temporary files ALWAYS
        logger.info(f"[Task:{task_id}] Cleaning up temporary files...")
        # Use the sync version of cleanup, as it's simple file operations
        file_handler.cleanup_files(temp_video_path, temp_audio_path)
        logger.info(f"[Task:{task_id}] Background processing finished.")
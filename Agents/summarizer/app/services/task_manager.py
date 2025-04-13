# app/services/task_manager.py
import logging
import uuid
import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List
from app.utils import file_handler
from app.db.mongodb import get_task_collection
from app.models.task import TaskStatus, TaskDocument
from app.core.config import settings
from app.services import document_processing, llm
#from app.services.document_processing import extract_markdown
from app.models.request import SummaryType

logger = logging.getLogger(__name__)

async def create_task_in_db(file_name: str, summary_type:SummaryType) -> uuid.UUID:
    """Creates a new task record in MongoDB and returns its task_id."""
    task_id = uuid.uuid4()
    task_doc = TaskDocument(
        task_id=task_id,
        file_name=file_name,
        status=TaskStatus.PENDING,
        summary_type=summary_type, # Convert enu
        created_at=datetime.datetime.now(datetime.timezone.utc),
        updated_at=datetime.datetime.now(datetime.timezone.utc)
    )
    collection = get_task_collection()
    
    insert_data = task_doc.model_dump(
        mode='json',
        by_alias=True,
        exclude={'id'}
    )
    
    insert_data['_id'] = task_id
    
    await collection.insert_one(insert_data)
    logger.info(f"Created task {task_id} for document {file_name} in DB.")
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
        {"_id": task_id},
        {"$set": update_fields}
    )
    if result.matched_count == 0:
        logger.error(f"Task ID {task_id} not found in DB for status update.")
    else:
        logger.info(f"Updated task {task_id} status to {status.value}" + (f" with error: {error_message}" if error_message else ""))

async def update_task_result(task_id: uuid.UUID, summary: str):
    """Updates the task with the final summary and sets status to DONE."""
    collection = get_task_collection()
    update_fields = {
        "summary": summary,
        #"summary_path": summary_path,
        "status": TaskStatus.DONE.value,
        "updated_at": datetime.datetime.now(datetime.timezone.utc),
        "error_message": None
    }
    result = await collection.update_one(
        {"_id": task_id},
        {"$set": update_fields}
    )
    if result.matched_count == 0:
        logger.error(f"Task ID {task_id} not found in DB for result update.")
    else:
        logger.info(f"Stored summary result for task {task_id} and marked as DONE.")

async def get_task_from_db(task_id: uuid.UUID) -> Optional[dict]:
    """Retrieves a task document from MongoDB by task_id."""
    collection = get_task_collection()
    task_data = await collection.find_one({"_id": task_id})
    return task_data

# --- Main Background Processing Functions ---
async def process_document_task(task_id: uuid.UUID, file_path: str, summary_type:SummaryType):
    """The background task performing the full document summarization pipeline."""
    logger.info(f"[Task:{task_id}] Starting background processing for document: {file_path}")

    try:
        await update_task_status(task_id, TaskStatus.DOWNLOADING)
        file_tmp_path=await file_handler.download_document_from_url(file_path)

        # 1. Update status: EXTRACTING
        await update_task_status(task_id, TaskStatus.EXTRACTING)

        # 2. Extract text from document
        image_caption=document_processing.get_image_info(file_tmp_path)
        text = await document_processing.extract_text_from_document(file_tmp_path, image_caption)

        logger.info(f"[Task:{task_id}] Text extracted from document")

        """
        text = ""        
        with open('test2.mmd', 'r', encoding='utf-8') as file:
           text = file.read()
        """
        
        # 4. Chunk document and analyze content
        chunks=document_processing.chunk_document_cosine(text)
        #chunks = document_processing.chunk_document(text)
        print(len(chunks))
        await update_task_status(task_id, TaskStatus.SUMMARIZING)

        logger.info(f"Generating summary")
        summary = await llm.generate_final_summary(chunks, summary_type)

        #correct_markdown_summary=extract_markdown(summary)

        logger.info(f"[Task:{task_id}] Summary generation successful.")

        await update_task_result(task_id, summary)
        logger.info(f"[Task:{task_id}] Task completed successfully.")

        
    except Exception as e:
        error_msg = f"Error processing document: {str(e)}"
        logger.error(f"[Task:{task_id}] {error_msg}")
        await update_task_status(task_id, TaskStatus.FAILED, error_msg)

'''
async def process_folder_task(task_id: uuid.UUID, folder_path: str):
    """The background task for processing all documents in a folder."""
    logger.info(f"[Task:{task_id}] Starting background processing for folder: {folder_path}")

    try:
        # 1. Update status: PROCESSING
        await update_task_status(task_id, TaskStatus.PROCESSING)
        
        # 2. Process all documents in the folder
        results = await document_processing.summarize_folder(folder_path)
        
        # 3. Update task with result summary
        summary_text = f"Processed {len(results)} documents in folder {folder_path}\n\n"
        for result in results:
            if "error" in result:
                summary_text += f"- {result['file_path']}: ERROR - {result['error']}\n"
            else:
                summary_text += f"- {result['file_path']}: Summary saved to {result['summary_path']}\n"
        
        # 4. Save the summary report
        folder_name = Path(folder_path).name
        summary_filename = f"{folder_name}_summary_report.md"
        summary_dir = Path(settings.SUMMARY_RESULTS_DIR)
        summary_dir.mkdir(exist_ok=True)
        summary_path = summary_dir / summary_filename
        
        with open(summary_path, "w", encoding="utf-8") as f:
            f.write(summary_text)
        
        # 5. Update task with result
        await update_task_result(task_id, summary_text, str(summary_path))
        
    except Exception as e:
        error_msg = f"Error processing folder: {str(e)}"
        logger.error(f"[Task:{task_id}] {error_msg}")
        await update_task_status(task_id, TaskStatus.FAILED, error_msg)
'''
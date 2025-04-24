# app/services/task_manager.py
import logging
import uuid
import datetime
from typing import Optional
from app.utils import file_handler
from app.db.mongodb import get_task_collection
from app.models.task import TaskStatus, TaskDocument
from app.services import document_processing

logger = logging.getLogger(__name__)

async def create_task_in_db(url: str) -> uuid.UUID:
    """Creates a new task record in MongoDB and returns its task_id."""
    task_id = uuid.uuid4()
    task_doc = TaskDocument(
        task_id=task_id,
        url=url,
        status=TaskStatus.PENDING,
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
    logger.info(f"Created task {task_id} for document {url} in DB.")
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

async def update_task_result(task_id: uuid.UUID, text: str):
    collection = get_task_collection()
    update_fields = {
        "text": text,
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

async def process_document_task(task_id: uuid.UUID, file_path: str):
    logger.info(f"[Task:{task_id}] Starting background processing for document: {file_path}")

    try:
        await update_task_status(task_id, TaskStatus.DOWNLOADING)
        file_tmp_path=await file_handler.download_document_from_url(file_path)
        # 1. Update status: EXTRACTING
        await update_task_status(task_id, TaskStatus.EXTRACTING)

        # 2. Extract text from document
        text = await document_processing.extract_text_from_document(file_tmp_path)

        logger.info(f"[Task:{task_id}] Text extracted from document")

        await update_task_result(task_id, text)
        logger.info(f"[Task:{task_id}] Task completed successfully.")
            
        
    except Exception as e:
        error_msg = f"Error processing document: {str(e)}"
        logger.error(f"[Task:{task_id}] {error_msg}")
        await update_task_status(task_id, TaskStatus.FAILED, error_msg)
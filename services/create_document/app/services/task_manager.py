# app/services/task_manager.py
import logging
import uuid
import datetime
from typing import Optional
from app.utils import file_handler
from app.db.mongodb import get_summary_collection, get_task_collection, get_upload_collection
from app.models.task import TaskStatus, TaskDocument
from app.core.config import settings
from app.services import document_processing, llm
#from app.services.document_processing import extract_markdown
from app.models.request import SummaryType
import httpx

logger = logging.getLogger(__name__)

async def create_task_in_db(summary_id: str) -> uuid.UUID:
    """Creates a new task record in MongoDB and returns its task_id."""
    task_id = uuid.uuid4()
    task_doc = TaskDocument(
        task_id=task_id,
        summary_id=summary_id,
        status=TaskStatus.PENDING,
        created_at=datetime.datetime.now(datetime.timezone.utc),
        updated_at=datetime.datetime.now(datetime.timezone.utc)
    )
    collection = get_upload_collection()
    
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
    collection = get_upload_collection()
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
    """Updates the task with the final summary and sets status to DONE."""
    collection = get_upload_collection()
    update_fields = {
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
    collection = get_upload_collection()
    task_data = await collection.find_one({"_id": task_id})
    return task_data


async def upload_document(summary_id: uuid.UUID, file_name:str, document_folder:str = None):
    """Uploads a document to the specified folder and returns the summary_id."""
    try:
        await update_task_status(summary_id, TaskStatus.GETTING_TEXT, error_msg)
        summary_text=extract_text(summary_id)
        
        await update_task_status(summary_id, TaskStatus.UPLOADING, error_msg)
        md_file_path=create_md_file(summary_text)

        files = {
            'markdownFile': (file_name,
                             open(md_file_path, 'rb'),
                             'text/markdown')
        }
        data = {
            'fileName': file_name,
            'folderName': document_folder or None
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                'http://localhost:3000/api/documents/upload',
                files=files,
                data=data,
                timeout=30.0
            )
            response.raise_for_status()

        logger.info(f"[Task:{summary_id}] Uploaded document via API, received status {response.status_code}")    
    except Exception as e:
        error_msg = f"Error uploading document: {str(e)}"
        logger.error(f"[Task:{summary_id}] {error_msg}")
        await update_task_status(summary_id, TaskStatus.FAILED, error_msg)




"""
async def extract_text_with_image_description(task_id: uuid.UUID, file_path: str):
    #The background task performing the full document summarization pipeline.
    logger.info(f"[Task:{task_id}] Starting background processing for document: {file_path}")

    try:
        if settings.TEST_PHASE==False:
            await update_task_status(task_id, TaskStatus.DOWNLOADING)
            file_tmp_path=await file_handler.download_document_from_url(file_path)

            # 1. Update status: EXTRACTING
            await update_task_status(task_id, TaskStatus.EXTRACTING)

            # 2. Extract text from document
            image_captions=document_processing.get_image_info(file_tmp_path)            
            text = await document_processing.extract_text_from_document(file_tmp_path, image_captions)
            logger.info(f"[Task:{task_id}] Text extracted from document")

            await update_task_result(task_id, text)
            logger.info(f"[Task:{task_id}] Task completed successfully.")
        else:
            await update_task_status(task_id, TaskStatus.DOWNLOADING)
            await update_task_status(task_id, TaskStatus.EXTRACTING)
            temp_file_path = settings.TEMP_DIR / f"test.md"
            with open(temp_file_path, 'r') as md_file:
                content=md_file.read()
            await update_task_result(content, temp_file_path)
            
    except Exception as e:
        error_msg = f"Error processing document: {str(e)}"
        logger.error(f"[Task:{task_id}] {error_msg}")
        await update_task_status(task_id, TaskStatus.FAILED, error_msg)
"""

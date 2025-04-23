# app/services/task_manager.py
import logging
import uuid
import datetime
from typing import Optional
from app.db.mongodb import  get_upload_collection
from app.models.task import TaskStatus, TaskDocument
from app.core.config import settings
import httpx
from app.utils.get_summary import get_text_by_id, create_md_file
from app.utils.get_formulas import *
import json


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
    logger.info(f"Created task {task_id}  in DB.")
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

async def update_task_result(task_id: uuid.UUID, document_id: str):
    """Updates the task with the final summary and sets status to DONE."""
    collection = get_upload_collection()
    update_fields = {
        
    }
    """Updates the task with the final summary and sets status to DONE."""
    collection = get_upload_collection()
    update_fields = {
        "status": TaskStatus.DONE.value,
        "created_document_id": document_id,
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


async def upload_document(jwt_token:str, task_id:uuid.UUID,  summary_id: uuid.UUID, file_name:str, document_folder:str = None):
    """Uploads a document to the specified folder and returns the summary_id."""
    try:
        await update_task_status(task_id, TaskStatus.GETTING_TEXT)
        summary_text=await get_text_by_id(summary_id)
        
        await update_task_status(task_id, TaskStatus.UPLOADING)

        #md_file_path=create_md_file(summary_text, summary_id)
        #modified_text, formula_urls= extract_formulas(summary_text)
        #modified_text, formula_urls, matches =extract_formulas(summary_text)

        process_document_with_formulas(summary_text, settings.UPLOAD_DOCUMENTS_URL, jwt_token)

        """        
        tokens=get_parsing(modified_text)
        
        current_index=1
        requests=[]

        for token in tokens:
            current_index=process_token(token, current_index, requests, formula_urls)
        
        current_index=1
        requests=[]
        
        for token in tokens:
            current_index=process_token_v1(token, current_index, requests, formula_urls)
        
        
        print(requests)
        data={}
        headers={}
        if requests:
            data = {
                'requests': requests,
            }

            headers={
                'Authorization': f'Bearer {jwt_token}'
            }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                settings.UPLOAD_DOCUMENTS_URL,
                #files=files,
                data=data,
                headers=headers,
                timeout=30.0
            )
            response.raise_for_status()

            #response_data = response.json()
            #document_id = response_data.get('fileId')
        
        #update_task_result(task_id, document_id)
        logger.info(f"[Task:{summary_id}] Uploaded document via API, received status {response.status_code}")    
        """
    except Exception as e:
        error_msg = f"Error uploading document: {str(e)}"
        logger.error(f"[Task:{summary_id}] {error_msg}")
        await update_task_status(task_id, TaskStatus.FAILED, error_msg)

# app/services/task_manager.py
import logging
import uuid
import datetime 
from typing import Optional
from app.utils import file_handler
from app.db.mongodb import get_summary_collection
from app.models.summary import SummaryStatus, SummaryDocument
from app.utils.get_text_from_db import get_text_by_id
from app.core.config import settings
from app.services import document_processing, llm
#from app.services.document_processing import extract_markdown
from app.models.request import SummaryType

logger = logging.getLogger(__name__)

async def create_summary_in_db(task_id: uuid.UUID, summary_type:SummaryType) -> uuid.UUID:
    """Creates a new task record in MongoDB and returns its task_id."""
    summary_id = uuid.uuid4()
    summary_doc = SummaryDocument(
        summary_id=summary_id,
        task_id=task_id,
        status=SummaryStatus.PENDING,
        summary_type=summary_type, # Convert enu
        created_at=datetime.datetime.now(datetime.timezone.utc),
        updated_at=datetime.datetime.now(datetime.timezone.utc)
    )
    collection = get_summary_collection()
    
    insert_data = summary_doc.model_dump(
        mode='json',
        by_alias=True,
        exclude={'id'}
    )
    
    insert_data['_id'] = summary_id
    
    await collection.insert_one(insert_data)
    logger.info(f"Created task {summary_id} for document {task_id} in DB.")
    return summary_id


async def update_summary_status(summary_id: uuid.UUID, status: SummaryStatus, error_message: Optional[str] = None):
    """Updates the status and updated_at time of a task in MongoDB."""
    collection = get_summary_collection()
    update_fields = {
        "status": status.value,
        "updated_at": datetime.datetime.now(datetime.timezone.utc),
    }
    if error_message:
        update_fields["error_message"] = error_message

    result = await collection.update_one(
        {"_id": summary_id},
        {"$set": update_fields}
    )
    if result.matched_count == 0:
        logger.error(f"Task ID {summary_id} not found in DB for status update.")
    else:
        logger.info(f"Updated task {summary_id} status to {status.value}" + (f" with error: {error_message}" if error_message else ""))

async def update_summary_result(task_id: uuid.UUID, summary: str):
    """Updates the task with the final summary and sets status to DONE."""
    collection = get_summary_collection()
    update_fields = {
        "summary": summary,
        "status": SummaryStatus.DONE.value,
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

async def get_summary_from_db(summary_id: uuid.UUID) -> Optional[dict]:
    """Retrieves a task document from MongoDB by task_id."""
    collection = get_summary_collection()
    task_data = await collection.find_one({"_id": summary_id})
    return task_data

async def generate_summary(summary_id: uuid.UUID, extracted_text_id:uuid.UUID,summary_type):
    """The background task performing the full document summarization pipeline."""
    logger.info(f"[Task:{summary_id}] Starting background processing for document: {extracted_text_id}")

    try:
        if settings.TEST_PHASE==False:
            await update_summary_status(summary_id, SummaryStatus.GETTING_TEXT)
            text=await get_text_by_id(extracted_text_id)
            
            await update_summary_status(summary_id, SummaryStatus.CHUNKING)
            if settings.CHUNCKER_TYPE=='standard':
                chunks=document_processing.chunk_document(text)
            else:
                chunks=document_processing.chunk_document_cosine(text)
            #chunks = document_processing.chunk_document(text)
            await update_summary_status(summary_id, SummaryStatus.SUMMARIZING)
            logger.info(f"Generating summary")
            summary = await llm.generate_final_summary(chunks, summary_type)

            logger.info(f"[Task:{summary_id}] Summary generation successful.") 

            await update_summary_result(summary_id, summary)
            logger.info(f"[Task:{summary_id}] Task completed successfully.")
        else:
            await update_summary_status(summary_id, SummaryStatus.GETTING_TEXT)
            await update_summary_status(summary_id, SummaryStatus.CHUNKING)
            await update_summary_status(summary_id, SummaryStatus.SUMMARIZING)
            temp_file_path = settings.TEMP_DIR / f"test.md"
            with open(temp_file_path, 'r') as md_file:
                content=md_file.read()
            await update_summary_result(content, temp_file_path)
            
        
    except Exception as e:
        error_msg = f"Error processing document: {str(e)}"
        logger.error(f"[Task:{summary_id}] {error_msg}") 
        await update_summary_status(summary_id, SummaryStatus.FAILED, error_msg)

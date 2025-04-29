# app/api/endpoints/tasks.py
import logging
import uuid
from venv import create
from fastapi import APIRouter, HTTPException, BackgroundTasks, Body, Path as FastApiPath

from app.models.request import TaskRequest
from app.models.task import TaskStatus, TaskCreationResponse, TaskStatusResponse, TaskResultResponse
from app.services import task_manager

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/", response_model=TaskCreationResponse, status_code=202)
async def submit_document_summary(
    background_tasks: BackgroundTasks,
    request_data: TaskRequest = Body(...)
):
    """
    Accepts the id of a task (containing an extracted text), creates a background task for summarizing,
    and returns the task ID.
    """
    logger.info(f"Received task submission for document: {request_data.summary_id}")
    try:
        # Create task entry in DB (status: PENDING)
        task_id = await task_manager.create_task_in_db(
            request_data.summary_id)

        # Add the processing function to background tasks
        background_tasks.add_task(
            task_manager.upload_document,
            request_data.jwt_token,
            task_id, #current task id
            request_data.summary_id, # id of the summary in DB
            request_data.uploaded_file_name,
            request_data.folder_name
        )
        logger.info(f"Scheduled background processing for task_id: {task_id}")

        # Return the task ID immediately
        return TaskCreationResponse(task_id=task_id)

    except Exception as e:
        logger.exception(f"Failed upload document text with id {request_data.summary_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to create processing task.")


@router.get("/{summary_id}/status", response_model=TaskStatusResponse)
async def get_summary_status(
    task_id: uuid.UUID = FastApiPath(..., description="The ID of the task to check.")
):
    """Retrieves the current status of uploading document task."""
    logger.debug(f"Request received for status of task_id: {task_id}")
    task_data = await task_manager.get_task_from_db(task_id)

    if not task_data:
        logger.warning(f"Task status request: Task ID {task_id} not found.")
        raise HTTPException(status_code=404, detail="Task not found.")

    # Return status response
    return TaskStatusResponse(
        summary_id=task_data['_id'],
        status=TaskStatus(task_data['status']),
        updated_at=task_data['updated_at']
    )

@router.get("/{summary_id}/result", response_model=TaskResultResponse)
async def get_summary_result(
     task_id: uuid.UUID = FastApiPath(..., description="The ID of the task to retrieve results for.")
):
    """
    Retrieves the result (summary or error) of a completed task.
    Returns current status if not yet finished.
    """
    logger.debug(f"Request received for result of task_id: {task_id}")
    task_Data = await task_manager.get_task_from_db(task_id)

    if not task_Data:
        logger.warning(f"Task result request: Task ID {task_id} not found.")
        raise HTTPException(status_code=404, detail="Task not found.")

    # Map the MongoDB dict to the Pydantic response model
    return TaskResultResponse(
         task_id=task_Data['_id'],
         status=TaskStatus(task_Data['status']),
         error=task_Data.get('error'),
         created_document_id=task_Data.get('created_document_id'),
         created_at=task_Data['created_at'],
         updated_at=task_Data['updated_at']
     )
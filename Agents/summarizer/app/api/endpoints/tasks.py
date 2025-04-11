# app/api/endpoints/tasks.py
import logging
import uuid
from fastapi import APIRouter, HTTPException, BackgroundTasks, Body, Path as FastApiPath
from typing import Optional

from app.models.request import DocumentRequest
from app.models.task import TaskStatus, TaskCreationResponse, TaskStatusResponse, TaskResultResponse
from app.services import task_manager

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/", response_model=TaskCreationResponse, status_code=202)
async def submit_document_task(
    background_tasks: oundTasks,
    request_data: DocumentRequest = Body(...)
):
    """
    Accepts a document file path, creates a background task for processing,
    and returns the task ID.
    """
    logger.info(f"Received task submission for document: {request_data.file_name}")
    try:
        # Create task entry in DB (status: PENDING)
        task_id = await task_manager.create_task_in_db(request_data.file_name)

        # Add the processing function to background tasks
        background_tasks.add_task(
            task_manager.process_document_task,
            task_id,
            request_data.file_name
        )
        logger.info(f"Scheduled background processing for task_id: {task_id}")

        # Return the task ID immediately
        return TaskCreationResponse(task_id=task_id)

    except Exception as e:
        logger.exception(f"Failed to submit task for document {request_data.file_name}: {e}")
        raise HTTPException(status_code=500, detail="Failed to create processing task.")

@router.get("/{task_id}/status", response_model=TaskStatusResponse)
async def get_task_status(
    task_id: uuid.UUID = FastApiPath(..., description="The ID of the task to check.")
):
    """Retrieves the current status of a processing task."""
    logger.debug(f"Request received for status of task_id: {task_id}")
    task_data = await task_manager.get_task_from_db(task_id)

    if not task_data:
        logger.warning(f"Task status request: Task ID {task_id} not found.")
        raise HTTPException(status_code=404, detail="Task not found.")

    # Return status response
    return TaskStatusResponse(
        task_id=task_data['_id'],
        status=TaskStatus(task_data['status']),
        updated_at=task_data['updated_at']
    )

@router.get("/{task_id}/result", response_model=TaskResultResponse)
async def get_task_result(
     task_id: uuid.UUID = FastApiPath(..., description="The ID of the task to retrieve results for.")
):
    """
    Retrieves the result (summary or error) of a completed task.
    Returns current status if not yet finished.
    """
    logger.debug(f"Request received for result of task_id: {task_id}")
    task_data = await task_manager.get_task_from_db(task_id)

    if not task_data:
        logger.warning(f"Task result request: Task ID {task_id} not found.")
        raise HTTPException(status_code=404, detail="Task not found.")

    # Map the MongoDB dict to the Pydantic response model
    return TaskResultResponse(
         task_id=task_data['_id'],
         status=TaskStatus(task_data['status']),
         file_name=task_data['file_name'],
         summary=task_data.get('summary'),
         summary_path=task_data.get('summary_path'),
         error=task_data.get('error_message'),
         created_at=task_data['created_at'],
         updated_at=task_data['updated_at']
     )
# app/api/v1/endpoints/tasks.py
import logging
import uuid
from fastapi import APIRouter, HTTPException, BackgroundTasks, Body, Path as FastApiPath # Use alias for Path
from typing import Optional

from app.models.request import VideoUrlRequest # Reuse request model
from app.models.task import TaskStatus, TaskCreationResponse, TaskStatusResponse, TaskResultResponse
from app.services import task_manager # Import the task service

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/", response_model=TaskCreationResponse, status_code=202) # 202 Accepted
async def submit_video_task(
    background_tasks: BackgroundTasks,
    request_data: VideoUrlRequest = Body(...)
):
    """
    Accepts a video URL, creates a background task for processing,
    and returns the task ID.
    """
    logger.info(f"Received task submission for URL: {request_data.video_url}")
    try:
        # 1. Create task entry in DB (status: PENDING)
        task_id = await task_manager.create_task_in_db(request_data.video_url)

        # 2. Add the processing function to background tasks
        background_tasks.add_task(
            task_manager.process_video_essay_task,
            task_id,
            request_data.video_url
        )
        logger.info(f"Scheduled background processing for task_id: {task_id}")

        # 3. Return the task ID immediately
        return TaskCreationResponse(task_id=task_id)

    except Exception as e:
        # Handle potential errors during DB interaction before background task starts
        logger.exception(f"Failed to submit task for URL {request_data.video_url}: {e}")
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

    # We only need a subset of fields for the status response
    return TaskStatusResponse(
        task_id=task_data['_id'], # Use _id which holds the UUID
        status=TaskStatus(task_data['status']), # Cast string back to Enum
        updated_at=task_data['updated_at']
    )

@router.get("/{task_id}/result", response_model=TaskResultResponse)
async def get_task_result(
     task_id: uuid.UUID = FastApiPath(..., description="The ID of the task to retrieve results for.")
):
    """
    Retrieves the result (essay or error) of a completed task.
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
         video_url=task_data['video_url'],
         essay=task_data.get('essay'), # Use .get for optional fields
         error=task_data.get('error_message'),
         created_at=task_data['created_at'],
         updated_at=task_data['updated_at']
     )
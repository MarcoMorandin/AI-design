# app/api/endpoints/tasks.py
import logging
import uuid
from fastapi import APIRouter, HTTPException, BackgroundTasks, Body, Path as FastApiPath
from typing import Optional

from app.models.request import SummaryRequest, TaskRequest
from app.models.summary import SummaryStatus, SummaryCreationResponse, SummaryStatusResponse, SummaryResultResponse
from app.services import summary_manager

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/", response_model=SummaryCreationResponse, status_code=202)
async def submit_document_summary(
    background_tasks: BackgroundTasks,
    request_data: SummaryRequest = Body(...)
):
    """
    Accepts the id of a task (containing an extracted text), creates a background task for summarizing,
    and returns the task ID.
    """
    logger.info(f"Received task submission for document: {request_data.task_id}")
    try:
        # Create task entry in DB (status: PENDING)
        summary_id = await summary_manager.create_summary_in_db(
            request_data.task_id,
            request_data.summary_type)

        # Add the processing function to background tasks
        background_tasks.add_task(
            summary_manager.generate_summary,
            summary_id,
            request_data.task_id,
            request_data.summary_type
        )
        logger.info(f"Scheduled background processing for task_id: {summary_id}")

        # Return the task ID immediately
        return SummaryCreationResponse(summary_id=summary_id)

    except Exception as e:
        logger.exception(f"Failed to submit task for document {request_data.task_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to create processing task.")


@router.get("/{summary_id}/status", response_model=SummaryStatusResponse)
async def get_summary_status(
    summary_id: uuid.UUID = FastApiPath(..., description="The ID of the task to check.")
):
    """Retrieves the current status of a summarizing task."""
    logger.debug(f"Request received for status of task_id: {summary_id}")
    task_data = await summary_manager.get_summary_from_db(summary_id)

    if not task_data:
        logger.warning(f"Task status request: Task ID {summary_id} not found.")
        raise HTTPException(status_code=404, detail="Task not found.")

    # Return status response
    return SummaryStatusResponse(
        summary_id=task_data['_id'],
        status=SummaryStatus(task_data['status']),
        updated_at=task_data['updated_at']
    )

@router.get("/{summary_id}/result", response_model=SummaryResultResponse)
async def get_summary_result(
     summary_id: uuid.UUID = FastApiPath(..., description="The ID of the task to retrieve results for.")
):
    """
    Retrieves the result (summary or error) of a completed task.
    Returns current status if not yet finished.
    """
    logger.debug(f"Request received for result of task_id: {summary_id}")
    summary_data = await summary_manager.get_summary_from_db(summary_id)

    if not summary_data:
        logger.warning(f"Task result request: Task ID {summary_id} not found.")
        raise HTTPException(status_code=404, detail="Task not found.")

    # Map the MongoDB dict to the Pydantic response model
    return SummaryResultResponse(
         summary_id=summary_data['_id'],
         status=SummaryStatus(summary_data['status']),
         summary=summary_data.get('summary'),
         summary_type=summary_data['summary_type'],
         error=summary_data.get('error'),
         created_at=summary_data['created_at'],
         updated_at=summary_data['updated_at']
     )
import logging
from .models.Task import Task, TaskStatus, TaskState, Message, Artifact
import asyncio
from datetime import datetime

from .models.Types import (
    GetTaskRequest,
    GetTaskResponse,
    CancelTaskRequest,
    CancelTaskResponse,
    SendTaskRequest,
    SendTaskResponse,
)

logger = logging.getLogger(__name__)


class TaskManager:
    def __init__(self):
        self.tasks: dict[str, Task] = {}

    def on_get_task(self, request: GetTaskRequest) -> GetTaskResponse:
        logger.info(f"Getting task {request.params.id}")
        task = self.tasks.get(request.params.id)
        if task is None:
            return GetTaskResponse(id=request.id, error="Task not found")

        return GetTaskResponse(id=request.id, result=task)

    def on_cancel_task(self, request: CancelTaskRequest) -> CancelTaskResponse:
        logger.info(f"Cancelling task {request.params.id}")
        task = self.tasks.get(request.params.id)
        if task is None:
            return CancelTaskResponse(id=request.id, error="Task not found")

        return CancelTaskResponse(id=request.id)

    async def _update_task(
        self,
        task_id: str,
        task_state: TaskState,
        response_text: str,
    ) -> Task:
        task = self.tasks[task_id]
        agent_response_parts = [
            {
                "type": "text",
                "text": response_text,
            }
        ]
        task.status = TaskStatus(
            state=task_state,
            message=Message(
                role="agent",
                parts=agent_response_parts,
            ),
            timestamp=datetime.now()
        )
        task.artifacts = [
            Artifact(
                parts=agent_response_parts,
            )
        ]
        return task

    async def _invoke(
        self, request: SendTaskRequest, swarm, agent
    ) -> SendTaskResponse:
        task_send_params = request.params
        query = self._get_user_query(task_send_params)
        messages = [{"role": "user", "content": query}]
        
        try:
            result = await swarm.run(agent=agent, messages=messages)
        except Exception as e:
            logger.error(f"Error invoking agent: {e}")
            raise ValueError(f"Error invoking agent: {e}")
    
        content = ""
        for part in result.messages:
            if part["role"] == "assistant":
                content = part["content"]

        return content

    async def on_send_task(
        self, request: SendTaskRequest, swarm, agent
    ) -> SendTaskResponse:
        task = self.tasks.get(request.params.id)
        if task is None:
            task = Task(
                id=request.params.id,
                sessionId=request.params.sessionId,
                status=TaskStatus(
                    state=TaskState.SUBMITTED,
                    message=request.params.message,
                    timestamp=datetime.now()
                ),
                history=[request.params.message],
            )
            self.tasks[request.params.id] = task

            # Update task to working state
            await self._update_task(
                task_id=request.params.id,
                task_state=TaskState.WORKING,
                response_text="Processing your request...",
            )

            # Invoke the agent
            content = await self._invoke(request, swarm, agent)

            # Update task to completed state
            task = await self._update_task(
                task_id=request.params.id,
                task_state=TaskState.COMPLETED,
                response_text=content,
            )

            return SendTaskResponse(id=request.id, result=task)
        
        # If task already exists, return current state
        return SendTaskResponse(id=request.id, result=task)

    def _get_user_query(self, task_params):
        """Extract user query from task parameters."""
        if hasattr(task_params, 'message') and task_params.message:
            # Extract text parts from the message
            parts = task_params.message.parts if hasattr(task_params.message, 'parts') else []
            query = []
            for part in parts:
                # Check if it's a TextPart object
                if hasattr(part, 'type') and part.type == 'text':
                    query.append(part.text)
                # Fallback for dictionary-style parts
                elif isinstance(part, dict) and part.get('type') == 'text':
                    query.append(part.get('text', ''))
            return ' '.join(query)
        return ''

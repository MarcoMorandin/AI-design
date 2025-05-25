from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import uvicorn

from .a2a.models.AgentCard import AgentCard
from .a2a.TaskManager import TaskManager
from .agent.agent import Agent
from .a2a.models.Types import (
    GetTaskRequest,
    CancelTaskRequest,
    SendTaskRequest,
)


class A2AServer:
    def __init__(
        self,
        agent: Agent,
        agent_card: AgentCard,
        task_manager: TaskManager,
        host="0.0.0.0",
        port=8000,
        endpoint="/",
    ):
        self.agent = agent
        self.agent_card = agent_card
        self.task_manager = task_manager
        self.host = host
        self.port = port
        self.endpoint = endpoint
        self.app = FastAPI(
            title="A2A Server", description="Agent-to-Agent Communication Server"
        )
        self.setup_routes(self.app)

    def setup_routes(self, app):
        @app.get("/.well-known/agent.json")
        async def a2a_agent_card():
            return self.agent_card.to_dict()

        @app.get("/")
        async def a2a_root_get():
            return await a2a_agent_card()

        @app.post("/tasks/send")
        async def a2a_tasks_send(request: Request):
            try:
                data = await request.json()
                task_request = SendTaskRequest(**data)
                response = await self.task_manager.on_send_task(
                    task_request, self.agent
                )
                return response.dict()
            except Exception as e:
                return JSONResponse(
                    status_code=500,
                    content={"error": f"Error processing task: {str(e)}"},
                )

        @app.post("/tasks/get")
        async def a2a_tasks_get(request: Request):
            try:
                data = await request.json()
                task_request = GetTaskRequest(**data)
                response = self.task_manager.on_get_task(task_request)
                return response.dict()
            except Exception as e:
                return JSONResponse(
                    status_code=500, content={"error": f"Error getting task: {str(e)}"}
                )

        @app.post("/tasks/cancel")
        async def a2a_tasks_cancel(request: Request):
            try:
                data = await request.json()
                task_request = CancelTaskRequest(**data)
                response = self.task_manager.on_cancel_task(task_request)
                return response.dict()
            except Exception as e:
                return JSONResponse(
                    status_code=500,
                    content={"error": f"Error canceling task: {str(e)}"},
                )

    def run(self):
        """Run the FastAPI server using uvicorn."""
        uvicorn.run(self.app, host=self.host, port=self.port)
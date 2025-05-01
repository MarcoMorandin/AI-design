from pydantic import BaseModel
from typing import Optional, Any, Dict, List
from .Task import Task, Message


class TaskParams(BaseModel):
    id: str
    sessionId: Optional[str] = None
    message: Optional[Message] = None


class GetTaskParams(BaseModel):
    id: str


class CancelTaskParams(BaseModel):
    id: str


class BaseRequest(BaseModel):
    id: str
    params: Any


class SendTaskRequest(BaseRequest):
    params: TaskParams


class GetTaskRequest(BaseRequest):
    params: GetTaskParams


class CancelTaskRequest(BaseRequest):
    params: CancelTaskParams


class BaseResponse(BaseModel):
    id: str
    error: Optional[str] = None
    result: Optional[Any] = None


class SendTaskResponse(BaseResponse):
    result: Optional[Task] = None


class GetTaskResponse(BaseResponse):
    result: Optional[Task] = None


class CancelTaskResponse(BaseResponse):
    pass

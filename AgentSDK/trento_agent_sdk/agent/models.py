from typing import List, Optional
from pydantic import BaseModel
from .agent import Agent


class Response(BaseModel):
    # Encapsulate the entire conversation output
    messages: List = []
    agent: Optional[Agent] = None


class Result(BaseModel):
    # Encapsulate the return value of a single function/tool call
    value: str = ""  # The result value as a string.
    agent: Optional[Agent] = None  # The agent instance, if applicable.

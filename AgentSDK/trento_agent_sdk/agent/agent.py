import json
import copy

import json
from google import genai
import re
from typing import List

from pydantic import BaseModel
from typing_extensions import Literal
from typing import Union, Callable, List, Optional
from ..tool.tool import Tool
from ..tool.tool_manager import ToolManager
import ast


class Agent(BaseModel):
    name: str = "Agent"
    model: str = "gemini-2.0-flash"
    instructions: Union[str, Callable[[], str]] = "You are a helpful agent."
    tool_manager: ToolManager = None

    class Config:
        arbitrary_types_allowed = True

    def get_instructions(self) -> str:
        """Return instructions, handling both string and callable cases."""
        return self.instructions() if callable(self.instructions) else self.instructions

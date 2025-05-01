import json
import copy
import re
import ast
from typing import Union, Callable, List, Optional

from google import genai
from pydantic import BaseModel
from typing_extensions import Literal

from ..tool.tool import Tool  # Fixed relative import
from ..tool.tool_manager import ToolManager  # Fixed relative import
from .agent import Agent


class Response(BaseModel):
    # Encapsulate the entire conversation output
    messages: List = []
    agent: Optional[Agent] = None


class Result(BaseModel):
    # Encapsulate the return value of a single function/tool call
    value: str = ""  # The result value as a string.
    agent: Optional[Agent] = None  # The agent instance, if applicable.

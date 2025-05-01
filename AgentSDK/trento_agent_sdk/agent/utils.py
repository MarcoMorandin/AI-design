import json
import copy

import json
from google import genai
import re
from typing import List

from pydantic import BaseModel
from typing_extensions import Literal
from typing import Union, Callable, List, Optional
from tool.tool import Tool
from tool.tool_manager import ToolManager
import ast


def pretty_print_messages(messages: List[dict]) -> None:
    """Print messages with colored formatting."""
    for message in messages:
        if message["role"] != "assistant":
            continue

        print(f"\033[94m{message['sender']}\033[0m:", end=" ")
        if message.get("content"):
            print(message["content"])

        tool_calls = message.get("tool_calls") or []
        if len(tool_calls) > 1:
            print()
        for tool_call in tool_calls:
            f = tool_call["function"]
            name, args = f["name"], f["arguments"]
            arg_str = json.dumps(json.loads(args)).replace(":", "=")
            print(f"\033[95m{name}\033[0m({arg_str[1:-1]})")

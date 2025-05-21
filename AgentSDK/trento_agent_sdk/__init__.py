# Import main components for easier access
from .logging_config import setup_logging
from .agent.agent import Agent
from .tool.tool_manager import ToolManager
from .tool.tool import Tool, get_function_info
from .a2a_client import A2AClient
from .a2a_server import A2AServer

# Define public API
__all__ = [
    "Agent",
    "ToolManager",
    "Tool",
    "get_function_info",
    "A2AClient",
    "A2AServer",
    "setup_logging",
]

# Initialize logging with default settings
# This can be overridden by calling setup_logging() with custom parameters
setup_logging()

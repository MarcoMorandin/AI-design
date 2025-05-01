from __future__ import annotations as _annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Any
from .tool import Tool
import asyncio


class ToolManager:
    """Manages FastMCP tools."""

    def __init__(self, warn_on_duplicate_tools: bool = True):
        self._tools: dict[str, Tool] = {}
        self.warn_on_duplicate_tools = warn_on_duplicate_tools

    def get_tool(self, name: str) -> Tool | None:
        """Get tool by name."""
        return self._tools.get(name)

    def list_tools(self) -> list[Tool]:
        """List all registered tools."""
        return list(self._tools.values())

    def add_tool(
        self,
        fn: Callable[..., Any],
        name: str | None = None,
        description: str | None = None,
    ) -> Tool:
        """Add a tool to the server."""
        tool = Tool.from_function(fn, name=name, description=description)
        existing = self._tools.get(tool.name)
        if existing:
            if self.warn_on_duplicate_tools:
                print(f"Tool already exists: {tool.name}")
                # logger.warning(f"Tool already exists: {tool.name}")
            return existing
        self._tools[tool.name] = tool
        return tool

    async def call_tool(
        self,
        name: str,
        arguments: dict[str, Any],
    ) -> Any:
        """Call a tool by name with arguments."""
        tool = self.get_tool(name)
        if not tool:
            raise Exception(f"Unknown tool: {name}")

        return await tool.run(arguments)

    def get_tool_info(
        self,
        name: str,
    ):
        tool = self.get_tool(name)
        if not tool:
            raise Exception(f"Unknown tool: {name}")

        return tool.get_tool_info()


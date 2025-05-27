from __future__ import annotations as _annotations

from pydantic import BaseModel, Field
import inspect
from typing import Any, Callable, Dict, List, Union
from .func_metadata import call_fn_with_arg


def _type_to_json_schema(py_type) -> str:
    """Convert Python type to JSON schema type string."""
    if py_type == str:
        return "string"
    elif py_type == int:
        return "integer"
    elif py_type == float:
        return "number"
    elif py_type == bool:
        return "boolean"
    elif py_type == list or py_type == List:
        return "array"
    elif py_type == dict or py_type == Dict:
        return "object"
    elif py_type == None or py_type == type(None):
        return "null"
    elif hasattr(py_type, "__origin__") and py_type.__origin__ == Union:
        # For typing.Union, use the first type as default
        if hasattr(py_type, "__args__") and len(py_type.__args__) > 0:
            return _type_to_json_schema(py_type.__args__[0])
    # Default to string for complex types
    return "string"


def get_function_info(fn, name, description):
    """
    Extract function info in OpenAI function calling format
    """
    try:
        signature = inspect.signature(fn)
    except ValueError as e:
        raise ValueError(
            f"Failed to get signature for function {fn.__name__}: {str(e)}"
        )

    parameters = {}
    for param_name, param in signature.parameters.items():
        param_type = param.annotation
        param_info = {
            "type": _type_to_json_schema(param_type),
            "description": "",  # Default empty description
        }

        # Try to get description from docstring if available
        if fn.__doc__:
            param_docs = fn.__doc__.split(f"{param_name}:")
            if len(param_docs) > 1:
                param_description = param_docs[1].split("\n")[0].strip()
                param_info["description"] = param_description

        parameters[param_name] = param_info

    # required parameters are those without a default value
    required = [
        param.name
        for param in signature.parameters.values()
        if param.default == inspect._empty
    ]

    return {
        "type": "function",
        "function": {
            "name": fn.__name__ or name,
            "description": fn.__doc__ or description or "",
            "parameters": {
                "type": "object",
                "properties": parameters,
                "required": required,
            },
        },
    }


class Tool(BaseModel):
    """Internal tool registration info."""

    fn: Callable[..., Any] = Field(exclude=True)
    name: str = Field(description="Name of the tool")
    description: str = Field(description="Description of what the tool does")
    parameters: dict[str, Any] = Field(description="JSON schema for tool parameters")
    is_async: bool = Field(description="Whether the tool is async")

    @classmethod
    def from_function(
        cls,
        fn: Callable[..., Any],
        name: str | None = None,
        description: str | None = None,
    ) -> Tool:
        """Create a tool from a function."""

        func_name = name or fn.__name__

        if func_name == "<lambda>":
            raise ValueError("You must provide a name for lambda functions")

        func_doc = description or fn.__doc__ or ""
        is_async = inspect.iscoroutinefunction(fn)

        # get metadata of the function (used to check during run)
        parameters = get_function_info(fn, name, description)

        return cls(
            fn=fn,
            name=func_name,
            description=func_doc,
            parameters=parameters,
            is_async=is_async,
        )

    def get_tool_info(self):
        if self.parameters is not None:
            return self.parameters
        else:
            parameters = get_function_info(self.fn, self.name, self.description)
            return parameters

    async def run(
        self,
        arguments: dict[str, Any],
    ) -> Any:
        """Run the tool with arguments."""
        try:
            return await call_fn_with_arg(self.fn, self.is_async, arguments)
        except Exception as e:
            raise Exception(f"Error executing tool {self.name}: {e}") from e

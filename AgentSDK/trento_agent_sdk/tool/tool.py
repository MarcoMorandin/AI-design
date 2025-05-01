from __future__ import annotations as _annotations

from pydantic import BaseModel, Field
import inspect
from typing import Any, Callable, get_type_hints, Optional
import json
from .func_metadata import call_fn_with_arg


def get_function_info(fn, name, description):

    try:
        signature = inspect.signature(fn)
    except ValueError as e:
        raise ValueError(
            f"Failed to get signature for function {fn.__name__}: {str(e)}"
        )

    parameters = {}
    for param in signature.parameters.values():
        param_type = param.annotation
        parameters[param.name] = {"type": param_type}

    # required parameters are those without a default value
    required = [
        param.name
        for param in signature.parameters.values()
        if param.default == inspect._empty
    ]

    # TODO: ---- Se vogliamo aggiungere il controllo e seguire il MCP →
    # forse ci sarebbe da convertirlo in json e poi da json a dict di nuovo e lavorare con pydantic ---

    return {
        "type": "function",
        "function": {
            "name": fn.__name__ or name,
            "description": fn.__doc__ or description,
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
        # fn_medatada: dict[str, Any] | None = None,
        # context_kwarg: str | None = None,
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

from ast import Dict
import inspect
import json
from collections.abc import Awaitable, Callable, Sequence
from typing import (
    Annotated,
    Any,
    ForwardRef,
)

from pydantic import BaseModel, ConfigDict, Field, WithJsonSchema, create_model
from pydantic._internal._typing_extra import eval_type_backport
from pydantic.fields import FieldInfo
from pydantic_core import PydanticUndefined

async def call_fn_with_arg(
        fn: Callable[..., Any] | Awaitable[Any],
        fn_is_async: bool,
        arguments: dict[str, Any],
    ) -> Any:
        """Call the given function with passed arguments"""

        if fn_is_async:
            if isinstance(fn, Awaitable):
                return await fn
            return await fn(**arguments)
        if isinstance(fn, Callable):
            return fn(**arguments)
        raise TypeError("fn must be either Callable or Awaitable")
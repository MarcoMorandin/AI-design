from collections.abc import Awaitable, Callable
from typing import (Any,)

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
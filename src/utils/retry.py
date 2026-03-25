"""Retry utilities."""

import asyncio
import functools
from collections.abc import Callable
from typing import Any, TypeVar, cast

T = TypeVar("T")


async def retry_with_backoff[T](
    func: Callable[..., T],
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exceptions: tuple[type[Exception], ...] = (Exception,),
) -> T:
    last_exception: Exception | None = None

    for attempt in range(max_attempts):
        try:
            if asyncio.iscoroutinefunction(func):
                coro = func()
                return cast(T, await coro)
            else:
                return func()
        except exceptions as e:
            last_exception = e
            if attempt < max_attempts - 1:
                delay = min(base_delay * (2**attempt), max_delay)
                await asyncio.sleep(delay)

    if last_exception:
        raise last_exception
    raise RuntimeError("Retry failed without exception")


def with_retry(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    exceptions: tuple[type[Exception], ...] = (Exception,),
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            return await retry_with_backoff(
                lambda: func(*args, **kwargs),
                max_attempts=max_attempts,
                base_delay=base_delay,
                exceptions=exceptions,
            )

        return wrapper  # type: ignore[return-value]

    return decorator

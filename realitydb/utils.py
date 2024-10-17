from __future__ import annotations

import asyncio
import json
import logging
import os
import shutil
import time
from dataclasses import dataclass, field
from functools import partial, reduce, wraps
from typing import Any, Awaitable, Callable, Coroutine, Type, TypeVar, Union, cast
from uuid import uuid4

import base64c as base64  # type: ignore
from cachetools import TTLCache, cached  # type: ignore
from requests import get
from typing_extensions import ParamSpec

T = TypeVar("T")
P = ParamSpec("P")


@dataclass
class RPCError(BaseException):
    code: int = field(default=-32000)
    message: str = field(default="Method not found or Malformed response")


def ttl_cache(
    func: Callable[P, T], *, maxsize: int = 1000, ttl: int = 60 * 60
) -> Callable[P, T]:
    cache = TTLCache(maxsize=maxsize, ttl=ttl)

    @cached(cache)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
        return func(*args, **kwargs)

    wrapper.__name__ = func.__name__
    return wrapper


def normalize_path(path: str) -> str:
    if path.startswith("http"):
        data = get(path, stream=True).raw
        path = f"/tmp/{uuid4()}"
        with open(path, "wb") as f:
            shutil.copyfileobj(data, f)
        return path
    if path.startswith("~"):
        path = os.path.expanduser(path)
    return os.path.normpath(path)


def ouid() -> str:
    return base64.urlsafe_b64encode(uuid4().bytes).decode("utf-8").rstrip("=")


def chunker(seq: str, size: int):
    return (seq[pos : pos + size] for pos in range(0, len(seq), size))


def get_logger(
    name: str | None = None,
    level: int = logging.DEBUG,
    format_string: str = json.dumps(
        {
            "timestamp": "%(asctime)s",
            "level": "%(levelname)s",
            "name": "%(name)s",
            "message": "%(message)s",
        }
    ),
) -> logging.Logger:
    """
    Configures and returns a logger with a specified name, level, and format.

    :param name: Name of the logger. If None, the root logger will be configured.
    :param level: Logging level, e.g., logging.INFO, logging.DEBUG.
    :param format_string: Format string for log messages.
    :return: Configured logger.
    """
    if name is None:
        name = "🚀 RockYouToo 🚀"
    logger_ = logging.getLogger(name)
    logger_.setLevel(level)
    if not logger_.handlers:
        ch = logging.StreamHandler()
        formatter = logging.Formatter(format_string)
        ch.setFormatter(formatter)
        logger_.addHandler(ch)
    return logging.getLogger(name)


logger = get_logger()


def exception_handler(
    func: Callable[P, Coroutine[Any, Any, T]]
) -> Callable[P, Coroutine[Any, Any, T]]:
    """
    Decorator to handle exceptions in a function.

    :param func: Function to be decorated.
    :return: Decorated function.
    """

    @wraps(func)
    async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
        try:
            func_ = cast(Awaitable[T], func(*args, **kwargs))
            return await func_
        except Exception as e:
            logger.error("%s: %s", e.__class__.__name__, e)
            raise RPCError(
                code=500,
                message=f"Internal Server Error: {e.__class__.__name__}:\n{e}",
            ) from e

    wrapper.__name__ = func.__name__
    return wrapper


def timing_handler(
    func: Callable[P, Coroutine[Any, Any, T]]
) -> Callable[P, Coroutine[Any, Any, T]]:
    """
    Decorator to measure the time taken by a function.

    :param func: Function to be decorated.
    :return: Decorated function.
    """

    async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
        start = time.time()
        result = await func(*args, **kwargs)
        logger.info("%s took %s seconds", func.__name__, time.time() - start)
        return result

    wrapper.__name__ = func.__name__
    return wrapper


def retry_handler(
    func: Callable[P, Coroutine[Any, Any, T]], retries: int = 3, delay: int = 1
) -> Callable[P, Coroutine[Any, Any, T]]:
    """
    Decorator to retry a function with exponential backoff.

    :param func: Function to be decorated.
    :param retries: Number of retries.
    :param delay: Delay between retries.
    :return: Decorated function.
    """

    @wraps(func)
    async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
        nonlocal delay
        for _ in range(retries):
            try:
                return await func(*args, **kwargs)
            except RPCError as e:
                logger.error("%s: %s", e.__class__.__name__, e)
                time.sleep(delay)
                delay *= 2
                continue
        raise RPCError(
            code=500,
            message="Exhausted retries",
        )

    wrapper.__name__ = func.__name__
    return wrapper


def handle(
    func: Callable[P, Coroutine[Any, Any, T]], retries: int = 3, delay: int = 1
) -> Callable[P, Union[T, Coroutine[Any, Any, T]]]:
    """
    Decorator to retry a function with exponential backoff and handle exceptions.

    :param func: Function to be decorated.
    :param retries: Number of retries.
    :param delay: Delay between retries.
    :return: Decorated function.
    """
    eb = partial(retry_handler, retries=retries, delay=delay)
    return cast(
        Callable[P, Union[T, Coroutine[Any, Any, T]]],
        reduce(lambda f, g: g(f), [exception_handler, timing_handler, eb], func),  # type: ignore
    )


def asyncify(func: Callable[P, T]) -> Callable[P, Coroutine[None, T, T]]:
    """
    Decorator to convert a synchronous function to an asynchronous function.

    :param func: Synchronous function to be decorated.
    :return: Asynchronous function.
    """

    @wraps(func)
    async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
        wrapper.__name__ = func.__name__
        return await asyncio.to_thread(func, *args, **kwargs)

    return wrapper


def singleton(cls: Type[T]) -> Type[T]:
    """
    Decorator that converts a class into a singleton.

    Args:
                                    cls (Type[T]): The class to be converted into a singleton.

    Returns:
                                    Type[T]: The singleton instance of the class.
    """
    instances: dict[Type[T], T] = {}

    @wraps(cls)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
        if cls not in instances:
            instances[cls] = cls(*args, **kwargs)
        return instances[cls]

    return cast(Type[T], wrapper)


def coalesce(*args: T) -> T | None:
    """
    Returns the first non-None argument.

    :param args: Arguments to be coalesced.
    :return: First non-None argument.
    """
    for arg in args:
        if arg is not None:
            return arg
    return None
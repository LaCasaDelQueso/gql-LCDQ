from typing import Any, Dict
from starlette.requests import Request
from gqlapi.lib.future.future.future import asyncio_run


def get_json(request: Request) -> Dict[Any, Any]:
    """ Get Response body as JSON

    Args:
        request (Request)

    Returns:
        str
    """
    return asyncio_run(request.json())


def get_body(request: Request) -> bytes:
    """ Get Response body as bytes

    Args:
        request (Request)

    Returns:
        bytes
    """
    return asyncio_run(request.body())

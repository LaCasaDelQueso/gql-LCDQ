from typing import Any, Dict
from starlette.requests import Request


async def serialize_request_headers(req: Request) -> Dict[str, Any]:
    """Serialize a request headers to a dict.
        It includes the IP Address if available.

    Args:
        req (Request): Starlette request

    Returns:
        Dict[str, Any]: Headers and session data
    """
    sess_data = dict(req.headers.items())
    # fetch client IP Address - if available
    if req.client and hasattr(req.client, "host"):
        sess_data["ipv4-address"] = req.client.host
    return sess_data

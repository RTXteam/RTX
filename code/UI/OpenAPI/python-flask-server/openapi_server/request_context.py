"""
Per-request client information for code that FastAPI does not hand the request to.

The generated API classes in impl/ only receive the parsed TRAPI body, so an HTTP
middleware records the client address here at the start of each request and the
query code reads it back. A ContextVar keeps concurrent requests apart.
"""
from contextvars import ContextVar

from fastapi import Request

_remote_address: ContextVar[str] = ContextVar("remote_address", default="???")


def get_remote_address() -> str:
    """Return the address of the client that sent the current request."""
    return _remote_address.get()


async def record_remote_address(request: Request, call_next):
    """HTTP middleware: remember the client address, preferring the first X-Forwarded-For hop
    (set by the reverse proxy in front of ARAX) over the socket peer address"""
    x_forwarded_for = request.headers.get("x-forwarded-for")
    if x_forwarded_for:
        remote_address = x_forwarded_for.split(",")[0].strip()
    elif request.client is not None:
        remote_address = request.client.host
    else:
        remote_address = "???"
    _remote_address.set(remote_address)
    return await call_next(request)

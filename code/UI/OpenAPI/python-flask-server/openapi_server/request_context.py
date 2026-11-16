"""
Per-request client information for code that FastAPI does not hand the request to.

The generated API classes in impl/ only receive the parsed TRAPI body, so an HTTP
middleware records the client address (and the app, for its app.state settings)
here at the start of each request and the query code reads them back. A ContextVar
keeps concurrent requests apart.
"""
import ipaddress
import re
from contextvars import ContextVar

from fastapi import FastAPI, Request

_remote_address: ContextVar[str] = ContextVar("remote_address", default="???")
_app: ContextVar[FastAPI | None] = ContextVar("app", default=None)
_public_api_base: ContextVar[str | None] = ContextVar("public_api_base", default=None)

# The TRAPI API root in a request path, e.g. /api/arax/v2.0
_API_ROOT_PATTERN = re.compile(r"^(.*?/api/arax/v[0-9.]+)(?:/|$)")


def get_remote_address() -> str:
    """Return the address of the client that sent the current request."""
    return _remote_address.get()


def get_app() -> FastAPI | None:
    """Return the FastAPI app handling the current request (FastAPI has no Flask-style current_app)."""
    return _app.get()


def get_public_api_base() -> str | None:
    """Return the public URL of this instance's TRAPI API root for the current request,
    e.g. https://arax.ncats.io/devED/api/arax/v2.0, or None if it can't be worked out."""
    return _public_api_base.get()


def _first(header_value: str | None) -> str | None:
    """First entry of a comma-separated forwarded header (a chain of proxies appends to it)"""
    if not header_value:
        return None
    return header_value.split(",")[0].strip() or None


def _instance_prefix() -> str:
    """Public path prefix of this instance when the proxy doesn't send X-Forwarded-Prefix.

    The Apache config serves a devarea at /<devarea>/api/arax/... and the main instance at
    /api/arax/..., and strips the prefix before forwarding, so fall back to that convention.
    """
    from RTXConfiguration import RTXConfiguration  # pylint: disable=import-outside-toplevel,import-error
    instance_name = RTXConfiguration().instance_name
    if instance_name in ("ARAX", "??", ""):
        return ""
    return f"/{instance_name}"


def _is_loopback(host: str) -> bool:
    """Whether a host[:port] names this machine (localhost, 127.x, ::1, 0.0.0.0) rather than a public name"""
    name = host.strip()
    if name.startswith("["):  # [ipv6]:port
        name = name[1:].split("]")[0]
    elif name.count(":") == 1:  # name:port or ipv4:port
        name = name.split(":")[0]
    if name.lower() == "localhost":
        return True
    try:
        address = ipaddress.ip_address(name)
    except ValueError:
        return False
    return address.is_loopback or address.is_unspecified


def _deployment_domain() -> str | None:
    """This deployment's public domain from code/config.domain (via RTXConfiguration), if it has one"""
    from RTXConfiguration import RTXConfiguration  # pylint: disable=import-outside-toplevel,import-error
    domain = (RTXConfiguration().domain or "").strip()
    if domain in ("", "??"):
        return None
    return domain


def compute_public_api_base(request: Request) -> str | None:
    """Work out the public TRAPI API root URL from the request and the reverse proxy's headers.

    Host and scheme come from X-Forwarded-Host / X-Forwarded-Proto when a proxy is in front,
    otherwise from the request itself. The path prefix the proxy stripped comes from
    X-Forwarded-Prefix, or from the devarea name when the proxy doesn't send it.

    On arax.ncats.io the chain is AWS load balancer (HTTPS) -> host nginx -> container Apache ->
    uvicorn, and the host nginx forwards Host 127.0.0.1:8081 and X-Forwarded-Proto http, so the
    public host and scheme are lost. When the forwarded host is a loopback address, use the
    deployment's config.domain over HTTPS instead.
    """
    match = _API_ROOT_PATTERN.match(request.url.path)
    if match is None:
        return None
    api_root = match.group(1)

    forwarded_host = _first(request.headers.get("x-forwarded-host"))
    forwarded_proto = _first(request.headers.get("x-forwarded-proto"))
    forwarded_prefix = request.headers.get("x-forwarded-prefix")

    if forwarded_host:
        host = forwarded_host
        # the public site is HTTPS; a proxy that terminates TLS may not say so
        scheme = forwarded_proto or "https"
        prefix = forwarded_prefix if forwarded_prefix is not None else _instance_prefix()
        domain = _deployment_domain() if _is_loopback(host) else None
        if domain:
            # an internal hop's address, not the public one (see the docstring)
            host = domain
            scheme = "https"
    else:
        host = request.url.netloc
        scheme = forwarded_proto or request.url.scheme
        prefix = forwarded_prefix or ""

    prefix = "/" + prefix.strip("/") if prefix.strip("/") else ""
    return f"{scheme}://{host}{prefix}{api_root}"


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
    _app.set(request.app)
    try:
        _public_api_base.set(compute_public_api_base(request))
    except Exception:  # pylint: disable=broad-exception-caught
        # never fail a request over this; callers treat None as "unknown"
        _public_api_base.set(None)
    return await call_next(request)

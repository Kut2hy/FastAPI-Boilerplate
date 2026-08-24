from fastapi import Request
from starlette.authentication import AuthCredentials, UnauthenticatedUser


def make_request(
    *,
    headers: dict[str, str] | None = None,
    user=None,
    scopes: list[str] | None = None,
    nonce: str = "test-nonce",
    language: str = "en",
    method: str = "GET",
    path: str = "/",
) -> Request:
    """Build a dummy ASGI Request for templating tests."""
    raw_headers = [(k.lower().encode("latin-1"), v.encode("latin-1")) for k, v in (headers or {}).items()]
    scope = {
        "type": "http",
        "method": method.upper(),
        "path": path,
        "headers": raw_headers,
        "user": user or UnauthenticatedUser(),
        "auth": AuthCredentials(scopes or []),
        "state": {"nonce": nonce, "language": language},
    }
    return Request(scope)

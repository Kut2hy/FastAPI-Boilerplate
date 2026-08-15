"""Application-level exception handlers.

Registered on the FastAPI app in ``app.main``. Handlers returning ``Response`` objects
are wired into Starlette's two implicit layers:

- ``ExceptionMiddleware`` (innermost) for handled/status-code exceptions.
- ``ServerErrorMiddleware`` (outermost) for uncaught exceptions (``Exception`` / ``500``).

Handlers here are content-negotiation ready: JSON today, JinjaX HTML later.

NOTE: Temporary AI generated placeholder
"""

from http import HTTPStatus

from fastapi import Request, status
from fastapi.responses import JSONResponse, Response

from app.i18n.context_translations import gettext


def _wants_html(request: Request) -> bool:
    """Return True when the client prefers an HTML error response.

    Checked against the Accept header; browsers send ``text/html`` while API clients
    typically send ``application/json`` or nothing.
    """
    accept = request.headers.get("accept", "")
    return "text/html" in accept and "application/json" not in accept


def _build_error_response(request: Request, status_code: int, detail: str) -> Response:
    """Build the error response payload for the given status code.

    Currently always JSON. When JinjaX templates land, the ``_wants_html`` branch below
    returns a TemplateResponse instead.
    """
    if _wants_html(request):
        # Future: return templates.TemplateResponse("error.html", context={...}, status_code=status_code)
        # Falls through to JSON for now.
        ...

    return JSONResponse(status_code=status_code, content={"detail": detail})


async def http_exception_handler(request: Request, exc: Exception) -> Response:
    """Handle Starlette/FastAPI HTTPException with the app-wide response shape."""
    status_code = getattr(exc, "status_code", status.HTTP_500_INTERNAL_SERVER_ERROR)
    detail = getattr(exc, "detail", HTTPStatus(status_code).phrase)
    return _build_error_response(request, status_code, str(detail))


async def unhandled_exception_handler(request: Request, exc: Exception) -> Response:  # noqa: ARG001
    """Handle any uncaught exception (registered as the app-level ``Exception`` handler).

    Runs in the outermost ServerErrorMiddleware layer, so request-scoped state set by
    user middleware (auth, locale) may not exist here — keep this handler self-sufficient
    and never delete client cookies: an unexpected bug must not log users out.
    """
    detail = gettext("Internal server error.")
    return _build_error_response(request, status.HTTP_500_INTERNAL_SERVER_ERROR, detail)

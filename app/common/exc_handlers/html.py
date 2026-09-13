"""Exception handlers for HTML responses."""

from http import HTTPStatus

from fastapi import Request, status

from app.core.templating.v1.response import HTMXTemplatedResponse, PartialResponseFragment


async def html_exception_handler(request: Request, exc: Exception) -> HTMXTemplatedResponse:
    """Handle exceptions and return an HTML response using HTMXTemplatedResponse.

    Args:
        request (Request): The FastAPI request object.
        exc (Exception): The exception that was raised.

    Returns:
        HTMXTemplatedResponse: The HTML response displaying the exception details.

    """
    status_code = getattr(exc, "status_code", status.HTTP_500_INTERNAL_SERVER_ERROR)
    detail = getattr(exc, "detail", HTTPStatus(status_code).phrase)

    return HTMXTemplatedResponse(
        request=request,
        status_code=status_code,
        title=detail,
        render_context={
            "html_code": status_code,
            "detail": detail,
            "request_id": str(request.state.uuid),
        },
        fragments=(
            PartialResponseFragment(
                name="main",
                path="base/exc.jinja.html",
            ),
        ),
        headers={
            "X-Request-ID": str(request.state.uuid),
            "X-Nonce": request.state.nonce,
            "HX-Nonce": request.state.nonce,
        }
    )

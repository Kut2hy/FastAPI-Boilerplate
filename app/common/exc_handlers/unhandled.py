"""Exception handler for unhandled exceptions."""

from fastapi import HTTPException, Request

from app.core.templating.v1.response import HTMXTemplatedResponse

from .html import html_exception_handler


async def unhandled_exception_handler(request: Request, exc: Exception) -> HTMXTemplatedResponse:
    """Handle unhandled exceptions by delegating to the HTML exception handler.

    Args:
        request (Request): The FastAPI request object.
        exc (Exception): The exception that was raised.

    Returns:
        HTMXTemplatedResponse: The HTML response displaying the exception details.

    """
    return await html_exception_handler(request, HTTPException(status_code=500))

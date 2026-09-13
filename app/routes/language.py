"""Route for setting the language preference."""

from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Form, HTTPException, Request, status
from fastapi.responses import RedirectResponse

from app.i18n.config import (
    COOKIE_LANGUAGE_KEY,
    IMPLEMENTED_LANGUAGES,
)
from app.i18n.context_translations import gettext as _

CURRENT_ENDPOINT = Path(__file__).stem
"""Current endpoint name, derived from the file name of this route module."""

router = APIRouter(
    tags=[
        CURRENT_ENDPOINT,
    ],
)


@router.put("/set-language")
async def set_language(
    request: Request, language: Annotated[str, Form(min_length=2, max_length=2)]
) -> RedirectResponse:
    """Set the language preference for the current user."""
    if language not in IMPLEMENTED_LANGUAGES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=_(f"Language '{language}' is not supported."),
        )

    response = RedirectResponse(
        url=request.headers.get("referer", "/"),
        status_code=status.HTTP_303_SEE_OTHER,
    )
    response.set_cookie(key=COOKIE_LANGUAGE_KEY, value=language)

    return response

"""Home endpoint."""

from pathlib import Path

from fastapi import APIRouter, Request, status

from app.common.middleware.server_timings import capture_duration
from app.core.templating.v1.response import HTMXTemplatedResponse, PartialResponseFragment
from app.i18n.context_translations import gettext as _

CURRENT_ENDPOINT = Path(__file__).stem
"""Current endpoint name, derived from the file name of this route module."""

router = APIRouter(
    tags=[
        CURRENT_ENDPOINT,
    ],
)


@router.get("/", response_class=HTMXTemplatedResponse)
@capture_duration()
async def get_home(request: Request) -> HTMXTemplatedResponse:
    """Endpoint for the home page.

    Args:
        request (Request): The incoming HTTP request.

    Returns:
        HTMXTemplatedResponse: The response for the home page.

    """
    return HTMXTemplatedResponse(
        request=request,
        status_code=status.HTTP_200_OK,
        title=_("Home page"),
        fragments=(
            PartialResponseFragment(
                name="main",
                path="routes/home.jinja.html",
            ),
        ),
    )

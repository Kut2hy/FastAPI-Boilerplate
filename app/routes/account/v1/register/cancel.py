"""Registration cancellation route."""

from pathlib import Path
from typing import Annotated

from fastapi import (
    APIRouter,
    Cookie,
    Depends,
    status,
)
from fastapi.responses import HTMLResponse

from app.common.dependencies.client import enforce_not_logged_in
from app.core.redis.dependencies import Redis, get_redis_client
from app.i18n.context_translations import gettext

from .__common import (
    REGISTRATION_COOKIE_KWARGS,
    REGISTRATION_FS_PATH_PARTS,
    REGISTRATION_URL,
    delete_registration,
)

CURRENT_ENDPOINT = Path(__file__).stem
"""Current endpoint name, derived from the file name of this route module."""

router = APIRouter(
    prefix=REGISTRATION_URL + f"/{CURRENT_ENDPOINT}",
    tags=[*REGISTRATION_FS_PATH_PARTS, CURRENT_ENDPOINT],
    dependencies=[Depends(enforce_not_logged_in())],
)


@router.get("/")
async def get_cancel(
    redis: Annotated[Redis, Depends(get_redis_client())],
    registration_token: Annotated[str | None, Cookie()] = None,
) -> HTMLResponse:
    """Endpoint to handle registration cancellation.

    Args:
        redis (Redis): The Redis client for accessing registration data.
        registration_token (str): The registration token from the cookies.

    Returns:
        HTMLResponse: The HTML response containing the cancellation page.

    """
    content = f"""
    <html>
        <head>
            <title>{gettext("Cancel Registration")}</title>
        </head>
        <body>
            <h1>{gettext("Cancel Registration")}</h1>
            <p>{gettext("Registration has been cancelled. You can start the registration again if you wish.")}</p>
            <a href="/"><button type="button">{gettext("Go to Home")}</button></a>
        </body>
    </html>
    """

    response = HTMLResponse(status_code=status.HTTP_200_OK, content=content)

    # NOTE: Both the cookie deletion and the Redis entry deletion are token agnostic.
    response.delete_cookie(**REGISTRATION_COOKIE_KWARGS)
    await delete_registration(redis, registration_token)

    return response

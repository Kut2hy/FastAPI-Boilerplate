"""Pure ASGI middleware that resolves the request locale into a ContextVar."""

from typing import TYPE_CHECKING

from starlette.datastructures import Headers

from app.i18n.config import DEFAULT_LANGUAGE, IMPLEMENTED_LANGUAGES
from app.i18n.context_translations import CURRENT_LOCALE

if TYPE_CHECKING:
    from starlette.types import ASGIApp, Receive, Scope, Send


class LocalizationMiddleware:
    """Resolve the client's preferred locale and expose it via the CURRENT_LOCALE ContextVar."""

    def __init__(self, app: ASGIApp) -> None:
        """Initialize the middleware with the ASGI application."""
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Set the locale ContextVar for the lifetime of the request, then delegate."""
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # Pre-set the default locale.
        locale = DEFAULT_LANGUAGE

        accept_language = Headers(scope=scope).get("accept-language", "")

        # Parse the Accept-Language header to find the first supported language.
        for part in accept_language.split(","):
            lang = part.split(";")[0].strip().lower()

            if not lang:
                continue

            if lang in IMPLEMENTED_LANGUAGES:
                locale = lang
                break

            primary = lang.split("-")[0]
            if primary in IMPLEMENTED_LANGUAGES:
                locale = primary
                break

        # Set the locale ContextVar for the lifetime of the request.
        token = CURRENT_LOCALE.set(locale)

        await self.app(scope, receive, send)

        # Reset the ContextVar to its previous state after the request is done.
        CURRENT_LOCALE.reset(token)

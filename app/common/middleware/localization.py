"""Pure ASGI middleware that resolves the request locale into a ContextVar."""

from typing import TYPE_CHECKING

from starlette.datastructures import Headers

from app.i18n.config import COOKIE_LANGUAGE_KEY, DEFAULT_LANGUAGE, IMPLEMENTED_LANGUAGES
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

        # Pre-set the defaults locale.
        default_lang, cookie_lang, header_lang = DEFAULT_LANGUAGE, None, None

        # Determine the preferred language from cookies or headers.
        try:
            # Extract headers from the ASGI scope.
            headers = Headers(scope=scope)

            cookie_lang = self.parse_cookies(headers.get("cookie", ""))

            # If cookie value is present -> no need to parse header value
            if cookie_lang is None:
                header_lang = self.parse_accept_language(headers.get("accept-language", ""))

        except Exception:
            cookie_lang = None
            header_lang = None

        # Set the locale ContextVar for the lifetime of the request.
        token = CURRENT_LOCALE.set(cookie_lang or header_lang or default_lang)

        await self.app(scope, receive, send)

        # Reset the ContextVar to its previous state after the request is done.
        CURRENT_LOCALE.reset(token)

    @staticmethod
    def parse_cookies(cookies: str) -> str | None:
        """Parse the cookies string and return the language if set and supported.

        Args:
            cookies (str): The value of the Cookie HTTP header.

        Returns:
            str | None: The language found in the cookies if it is supported, or None otherwise.

        """
        for cookie in cookies.split(";"):
            key, _, value = cookie.strip().partition("=")

            if key == COOKIE_LANGUAGE_KEY and value in IMPLEMENTED_LANGUAGES:
                return value

        return None

    @staticmethod
    def parse_accept_language(accept_language: str) -> str | None:
        """Parse the Accept-Language header and return the first supported language.

        Args:
            accept_language (str): The value of the Accept-Language HTTP header.

        Returns:
            str | None: The first supported language found, or None if none are supported.

        """
        for part in accept_language.split(","):
            lang = part.split(";")[0].strip().lower()

            if not lang:
                continue

            if lang in IMPLEMENTED_LANGUAGES:
                return lang

            primary = lang.split("-")[0]
            if primary in IMPLEMENTED_LANGUAGES:
                return primary

        return None

"""JWT middleware for FastAPI."""

from datetime import datetime, timezone
from logging import getLogger
from typing import TYPE_CHECKING, overload

from asyncpg import InterfaceError, PostgresError
from fastapi import status
from fastapi.responses import JSONResponse
from jwt import InvalidTokenError
from starlette.requests import HTTPConnection

from app.common.header_encoding import to_header_name_fmt, to_header_value_fmt
from app.common.middleware.asgi_cookies import delete_cookie, set_cookie
from app.core.jwt.access_token import ACCESS_TOKEN_COOKIE_KWARGS, AccessToken
from app.core.jwt.credentials import FrozenAuthCredentials
from app.core.jwt.exceptions import MissingJWTClaimsError
from app.core.jwt.refresh_token import REFRESH_TOKEN_COOKIE_KWARGS, RefreshToken
from app.core.jwt.users import AuthenticatedUser, UnauthenticatedUser
from app.i18n.context_translations import gettext
from app.piccolo.tables.refresh_token import regenerate_access_token

if TYPE_CHECKING:
    from starlette.types import ASGIApp, Message, Receive, Scope, Send

SET_COOKIE_HEADER = to_header_name_fmt("set-cookie")
"""Pre-encoded header name for 'Set-Cookie' to avoid repeated encoding in the middleware."""

ERROR_LOGGER = getLogger("uvicorn.error")


class JWTMiddleware:
    """Pure ASGI middleware to handle JWT authentication."""

    def __init__(self, app: ASGIApp) -> None:
        """Initialize the JWTMiddleware with the ASGI application.

        Args:
            app (ASGIApp): The ASGI application to wrap with the middleware.

        """
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Process the incoming request, resolving the caller's authentication state.

        Args:
            scope (Scope): The ASGI scope containing request information.
            receive (Receive): The ASGI receive callable.
            send (Send): The ASGI send callable.

        """
        # ==============================================================================================================
        # Non-HTTP requests (WebSocket, lifespan) are passed through without JWT processing.
        # ==============================================================================================================
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # Create an HTTPConnection object to access request headers and cookies
        connection = HTTPConnection(scope)

        # Preset the user and auth in the scope to unauthenticated values
        scope["user"] = UnauthenticatedUser()
        scope["auth"] = FrozenAuthCredentials(scopes=[])

        # Extract the access token and refresh token from cookies, if they exist
        access_token_cookie_str = connection.cookies.get(AccessToken.cookies_name)
        refresh_token_cookie_str = connection.cookies.get(RefreshToken.cookies_name)

        # ==============================================================================================================
        # Guest / Unauthenticated access
        # ==============================================================================================================
        if access_token_cookie_str is None and refresh_token_cookie_str is None:
            await self.app(scope, receive, send)
            return

        # Decision flags resolved by the token logic below. The downstream app is always invoked
        # outside the try/except so endpoint exceptions propagate to the app-level handlers.
        new_access_token: AccessToken | None = None
        delete_cookies = False

        try:
            access_token = self.validate_token(access_token_cookie_str, AccessToken)
            if isinstance(access_token, AccessToken):
                self.set_auth_context(scope, access_token)

                await self.app(scope, receive, send)
                return

            refresh_token = self.validate_token(refresh_token_cookie_str, RefreshToken)
            if isinstance(refresh_token, RefreshToken):
                # ==================================================================================================
                # Authenticated access with token regeneration using valid refresh token
                # ==================================================================================================
                # DB lookup ensures the refresh token was issued by this site, is not revoked,
                # and has not expired. None means the token is no longer trusted.
                regenerated_access_token = await regenerate_access_token(refresh_token)

                if regenerated_access_token is not None:
                    self.set_auth_context(scope, regenerated_access_token)
                    new_access_token = regenerated_access_token

                else:
                    delete_cookies = True

            else:
                # ==================================================================================================
                # Unauthenticated access with invalid refresh token
                # ==================================================================================================
                delete_cookies = True

        except PostgresError, InterfaceError, OSError, TimeoutError:
            ERROR_LOGGER.exception("Database error while processing JWT authentication.")
            await self.on_error_response(
                scope,
                receive,
                send,
                status.HTTP_503_SERVICE_UNAVAILABLE,
                gettext("Service unavailable. Try again later."),
            )
            return

        except Exception:
            # Log with traceback, then let the app-level catch-all handler
            # (ServerErrorMiddleware / @app.exception_handler(Exception)) create response
            ERROR_LOGGER.exception("Unexpected error while processing JWT authentication.")
            raise

        # ==============================================================================================================
        # Downstream invocation — deliberately outside the try/except above.
        # ==============================================================================================================
        if delete_cookies:
            await self.response_with_cookie_deletion(self.app, scope, receive, send)
            return

        if new_access_token is not None:
            await self.response_with_token_regeneration(self.app, scope, receive, send, access_token=new_access_token)
            return

        await self.app(scope, receive, send)

    @overload
    @staticmethod
    def validate_token(token_str: str | None, token_class: type[AccessToken]) -> AccessToken | None: ...

    @overload
    @staticmethod
    def validate_token(token_str: str | None, token_class: type[RefreshToken]) -> RefreshToken | None: ...

    @staticmethod
    def validate_token(
        token_str: str | None, token_class: type[AccessToken | RefreshToken]
    ) -> AccessToken | RefreshToken | None:
        """Validate a JWT token string using the specified token class.

        Only ``InvalidTokenError`` (bad signature, expired, wrong audience/issuer — i.e. client
        supplied garbage) is treated as "invalid token" and returns None. Structural failures
        (missing required claims, malformed UUIDs, wrong types) indicate a token WE minted
        incorrectly — those propagate so they surface as a 500 instead of being masked as a
        routine auth failure.

        Args:
            token_str (str | None): The JWT token string to validate.
            token_class (type): The class of the token to validate against (AccessToken or RefreshToken).

        Returns:
            AccessToken | RefreshToken | None: The validated token instance if valid, None otherwise.

        Raises:
            MissingJWTClaimsError: When a correctly-signed token is missing required claims.

        """
        if token_str is None:
            return None

        try:
            token = token_class.from_string(token_str, leeway=token_class.acceptable_leeway)

            if isinstance(token, AccessToken):
                if "alias" not in token.extra_claims or not token.extra_claims["alias"]:
                    raise MissingJWTClaimsError("Access token is missing the required 'alias' claim.")

                if "roles" not in token.extra_claims:
                    raise MissingJWTClaimsError("Access token is missing the required 'roles' claim.")

        except InvalidTokenError:
            return None

        return token

    @staticmethod
    def set_auth_context(scope: Scope, access_token: AccessToken) -> None:
        """Populate the scope's user/auth from a valid access token's claims.

        A correctly-signed access token that is missing the required ``alias`` claim (or carries a
        blank one) was minted incorrectly by this application — that is a bug, not an auth
        failure, so it raises rather than degrading silently.

        Args:
            scope (Scope): The ASGI scope to mutate.
            access_token (AccessToken): The validated access token to read claims from.

        Raises:
            MissingJWTClaimsError: If the required ``alias`` claim is missing or empty.

        """
        if "alias" not in access_token.extra_claims or not access_token.extra_claims["alias"]:
            raise MissingJWTClaimsError("Access token is missing the required 'alias' claim.")

        if "roles" not in access_token.extra_claims:
            raise MissingJWTClaimsError("Access token is missing the required 'roles' claim.")

        username = access_token.extra_claims["alias"]
        roles = access_token.extra_claims["roles"]

        scope["user"] = AuthenticatedUser(username=username, uuid=access_token.subject)
        scope["auth"] = FrozenAuthCredentials(scopes=roles.strip().split(",") if roles else [])

    @staticmethod
    async def response_with_cookie_deletion(
        app: ASGIApp,
        scope: Scope,
        receive: Receive,
        send: Send,
    ) -> None:
        """ASGI response "getter" that wraps the send callable to delete cookies in the response.

        Args:
            app (ASGIApp): The ASGI application to wrap with the middleware.
            scope (Scope): The ASGI scope containing request information.
            receive (Receive): The ASGI receive callable.
            send (Send): The ASGI send callable.

        """

        async def _wrapper(message: Message) -> None:
            if message["type"] == "http.response.start":
                message["headers"].extend(
                    (
                        (SET_COOKIE_HEADER, to_header_value_fmt(delete_cookie(**REFRESH_TOKEN_COOKIE_KWARGS))),
                        (SET_COOKIE_HEADER, to_header_value_fmt(delete_cookie(**ACCESS_TOKEN_COOKIE_KWARGS))),
                    )
                )

            await send(message)

        await app(scope, receive, _wrapper)

    @staticmethod
    async def response_with_token_regeneration(
        app: ASGIApp,
        scope: Scope,
        receive: Receive,
        send: Send,
        access_token: AccessToken,
    ) -> None:
        """ASGI response "getter" that wraps the send callable to regenerate the access token in the response.

        Args:
            app (ASGIApp): The ASGI application to wrap with the middleware.
            scope (Scope): The ASGI scope containing request information.
            receive (Receive): The ASGI receive callable.
            send (Send): The ASGI send callable.
            access_token (AccessToken): The new access token to set in the response.

        """

        async def _wrapper(message: Message) -> None:
            if message["type"] == "http.response.start":
                message["headers"].extend(
                    (
                        (
                            SET_COOKIE_HEADER,
                            to_header_value_fmt(
                                set_cookie(
                                    **ACCESS_TOKEN_COOKIE_KWARGS,
                                    value=str(access_token),
                                    expires=datetime.fromtimestamp(access_token.expiration, tz=timezone.utc),
                                )
                            ),
                        ),
                    ),
                )

            await send(message)

        await app(scope, receive, _wrapper)

    @staticmethod
    async def on_error_response(scope: Scope, receive: Receive, send: Send, status_code: int, detail: str) -> None:
        """Send an error response with the given status code and detail.

        Args:
            scope (Scope): The ASGI scope containing request information.
            receive (Receive): The ASGI receive callable.
            send (Send): The ASGI send callable.
            status_code (int): The HTTP status code for the error response.
            detail (str): The detail message for the error response.

        """
        response = JSONResponse(status_code=status_code, content={"detail": detail})
        await response(scope, receive, send)

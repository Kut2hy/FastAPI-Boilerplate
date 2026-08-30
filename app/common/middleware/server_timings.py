"""Middleware for measuring and logging server timings for each request."""

from functools import wraps
from time import perf_counter
from typing import TYPE_CHECKING

from app.app_config import APP_SETTINGS
from app.common.context_vars import ServerTimingAPI
from app.common.header_encoding import to_header_name_fmt, to_header_value_fmt

if TYPE_CHECKING:
    from collections.abc import Callable

    from starlette.types import ASGIApp, Message, Receive, Scope, Send

DEV_MODE = APP_SETTINGS.in_development
"""Flag indicating whether the application is running in development mode."""

SERVER_TIMINGS_HEADER = to_header_name_fmt("Server-Timing")
"""Pre-encoded header name for 'Server-Timing' to avoid repeated encoding in the middleware."""


def capture_duration() -> Callable[[Callable], Callable]:
    """Server timing decorator to measure the execution time of a function and store it in the context variable.

    Returns:
        Callable: A decorator that wraps the target function to measure its execution time.

    """
    def _decorator(func: Callable) -> Callable:

        # NOTE: Multiple Ruff rules are disabled here. As there is no way to annotate the return type or arguments.
        @wraps(func)
        async def _wrapper(*args, **kwargs):  # noqa: ANN002, ANN003, ANN202
            start_time = perf_counter()
            result = await func(*args, **kwargs)
            end_time = perf_counter()

            # Store the timing in the context variable
            server_timings = ServerTimingAPI.get() or {}
            ServerTimingAPI.set({**server_timings, func.__name__: (end_time - start_time) * 1000})

            return result

        return _wrapper

    return _decorator


class ServerTimingsMiddleware:
    """Pure ASGI middleware to inject server timing API headers into HTTP responses."""

    def __init__(self, app: ASGIApp) -> None:
        """Initialize the ServerTimingsMiddleware with the ASGI application.

        Args:
            app (ASGIApp): The ASGI application to wrap with the middleware.

        """
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Process the incoming request and inject server timing headers into the response.

        Args:
            scope (Scope): The ASGI scope containing request information.
            receive (Receive): The ASGI receive callable.
            send (Send): The ASGI send callable.

        """
        # Only enable the middleware in development mode for security reasons.
        if not DEV_MODE:
            await self.app(scope, receive, send)
            return

        # Only handle HTTP; pass lifespan/websocket straight through.
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def send_with_headers(message: Message) -> None:
            if message["type"] == "http.response.start":
                # Headers can only be appended on the response-start frame,
                # and only BEFORE it is sent. Retrieve the server timings
                # from the context variable.
                server_timings = ServerTimingAPI.get()

                if server_timings:
                    # Append the Server-Timing header to the response headers.
                    message.setdefault("headers", []).extend(
                        (
                            (
                                SERVER_TIMINGS_HEADER,
                                to_header_value_fmt(
                                    ", ".join(f"{name};dur={duration:.2f}" for name, duration in server_timings.items())
                                ),
                            ),
                        )
                    )

            await send(message)

        await self.app(scope, receive, send_with_headers)

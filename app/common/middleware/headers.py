"""Pure ASGI middleware for security headers."""

from secrets import token_urlsafe
from typing import TYPE_CHECKING
from uuid import uuid4

from app.common.header_encoding import to_header_name_fmt, to_header_value_fmt

if TYPE_CHECKING:
    from starlette.types import ASGIApp, Message, Receive, Scope, Send


# ======================================================================================================================
# Per request dynamic headers (nonce, request ID, CSP)
# ======================================================================================================================

X_IDENTIFIER_HEADER = to_header_name_fmt("X-Request-ID")
"""Header name for the unique request identifier."""


X_NONCE_HEADER = to_header_name_fmt("X-Nonce")
"""Header name for the nonce value used in Content Security Policy."""


HX_NONCE_HEADER = to_header_name_fmt("HX-Nonce")
"""Header name for the nonce value used by HTMX."""


_CSP_OPTIONS = {
    "default-src": "'self'",
    "script-src": "'self' %(nonce_hash)s https://cdn.jsdelivr.net 'strict-dynamic'",
    "style-src": "'self'",
    "img-src": "'self' data:",
    "font-src": "'self' https:",
    "connect-src": "'self'",
    "frame-src": "'self'",
    "frame-ancestors": "'none'",
    "object-src": "'none'",
    "base-uri": "'self'",
    "form-action": "'self'",
}

CSP_HEADER = to_header_name_fmt("Content-Security-Policy")
CSP_OPTIONS = to_header_value_fmt(";".join(f"{k} {v}" for k, v in _CSP_OPTIONS.items()))
"""Content Security Policy (CSP) headers. << nonce_hash >> will be replaced with the actual nonce hash."""

# ======================================================================================================================
# Static security headers
# ======================================================================================================================

X_CONTENT_TYPE_OPTIONS = (
    to_header_name_fmt("X-Content-Type-Options"),
    to_header_value_fmt("nosniff"),
)
"""Header to prevent MIME-type sniffing."""

X_FRAME_OPTIONS = (
    to_header_name_fmt("X-Frame-Options"),
    to_header_value_fmt("DENY"),
)
"""Header to prevent clickjacking by disallowing framing."""


REFERRER_POLICY = (
    to_header_name_fmt("Referrer-Policy"),
    to_header_value_fmt("strict-origin-when-cross-origin"),
)
"""Header to control the amount of referrer information sent with requests."""


PERMISSIONS_POLICY = (
    to_header_name_fmt("Permissions-Policy"),
    to_header_value_fmt(
        "accelerometer=(), autoplay=(), camera=(), display-capture=(), "
        "encrypted-media=(), fullscreen=(self), geolocation=(), gyroscope=(), "
        "magnetometer=(), microphone=(), midi=(), payment=(), usb=()"
    ),
)
"""Header to disable powerful browser features by default."""


CROSS_ORIGIN_OPENER_POLICY = (
    to_header_name_fmt("Cross-Origin-Opener-Policy"),
    to_header_value_fmt("same-origin"),
)
"""Header to process-isolate this origin to defend against cross-origin attacks (Spectre, XS-Leaks)."""


CROSS_ORIGIN_EMBEDDER_POLICY = (
    to_header_name_fmt("Cross-Origin-Embedder-Policy"),
    to_header_value_fmt("require-corp"),
)
"""Header to require cross-origin resources to be loaded with CORS, which is necessary for COOP to work."""


CROSS_ORIGIN_RESOURCE_POLICY = (
    to_header_name_fmt("Cross-Origin-Resource-Policy"),
    to_header_value_fmt("same-origin"),
)
"""Header to prevent other origins from loading this site's resources."""


X_PERMITTED_CROSS_DOMAIN_POLICIES = (
    to_header_name_fmt("X-Permitted-Cross-Domain-Policies"),
    to_header_value_fmt("none"),
)
"""Header to block Adobe cross-domain policy files."""


VARY_HEADER = (
    to_header_name_fmt("Vary"),
    to_header_value_fmt("HX-Request-Type, Accept-Language"),
)
"""Header to indicate that the response varies based on the HX-Request-Type and Accept-Language headers."""


class HeaderMiddleware:
    """Pure ASGI middleware to inject security-related headers into HTTP responses."""

    def __init__(self, app: ASGIApp) -> None:
        """Initialize the HeaderMiddleware with the ASGI application.

        Args:
            app (ASGIApp): The ASGI application to wrap with the middleware.

        """
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Process the incoming request and inject security headers into the response.

        Args:
            scope (Scope): The ASGI scope containing request information.
            receive (Receive): The ASGI receive callable.
            send (Send): The ASGI send callable.

        """
        # Only handle HTTP; pass lifespan/websocket straight through.
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # Per-request values, computed once before the response starts.
        request_id = uuid4()
        nonce = token_urlsafe(nbytes=32)

        # Stash the nonce/id where downstream code can read it (replaces request.state.*).
        state = scope.setdefault("state", {})
        state["nonce"] = nonce
        state["uuid"] = request_id

        async def send_with_headers(message: Message) -> None:
            # Headers can only be appended on the response-start frame.
            if message["type"] == "http.response.start":
                encoded_nonce = to_header_value_fmt(nonce)
                encoded_request_id = to_header_value_fmt(str(request_id))

                message["headers"].extend(
                    (
                        (X_IDENTIFIER_HEADER, encoded_request_id),
                        (X_NONCE_HEADER, encoded_nonce),
                        (HX_NONCE_HEADER, encoded_nonce),
                        (CSP_HEADER, CSP_OPTIONS % {b"nonce_hash": b"'nonce-" + encoded_nonce + b"'"}),
                        X_CONTENT_TYPE_OPTIONS,
                        X_FRAME_OPTIONS,
                        REFERRER_POLICY,
                        PERMISSIONS_POLICY,
                        CROSS_ORIGIN_OPENER_POLICY,
                        CROSS_ORIGIN_EMBEDDER_POLICY,
                        CROSS_ORIGIN_RESOURCE_POLICY,
                        X_PERMITTED_CROSS_DOMAIN_POLICIES,
                        VARY_HEADER,
                    )
                )

            await send(message)

        await self.app(scope, receive, send_with_headers)

"""FastAPI application entry point."""

from importlib import import_module
from logging import getLogger

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.app_config import APP_SETTINGS
from app.common.exceptions import http_exception_handler, unhandled_exception_handler
from app.common.middleware.headers import HeaderMiddleware
from app.common.middleware.localization import LocalizationMiddleware
from app.common.middleware.server_timings import ServerTimingsMiddleware
from app.core.jwt.middleware import JWTMiddleware
from app.life_cycle import life_cycle

LOGGER = getLogger(__name__)
"""Logger for the FastAPI application."""

DEV_MODE = APP_SETTINGS.in_development
"""Flag indicating whether the application is running in development mode."""

ALLOWED_HOSTS = [str(APP_SETTINGS.host), f"{APP_SETTINGS.host}:{APP_SETTINGS.port}"]
"""Host header values accepted by the application."""

ALLOWED_ORIGINS = [f"http://{APP_SETTINGS.host}:{APP_SETTINGS.port}"]
"""Origins accepted by the CORS middleware."""

if APP_SETTINGS.public_host:
    ALLOWED_HOSTS.append(APP_SETTINGS.public_host)
    ALLOWED_ORIGINS.append(f"https://{APP_SETTINGS.public_host}")

# ======================================================================================================================
# FastAPI application instance
# ======================================================================================================================
app = FastAPI(
    title=APP_SETTINGS.title,
    version=APP_SETTINGS.version,
    lifespan=life_cycle,
    openapi_url="/openapi.json" if DEV_MODE else None,
    docs_url="/docs" if DEV_MODE else None,
    redoc_url="/redoc" if DEV_MODE else None,
)

# ======================================================================================================================
# Exception handlers
# ======================================================================================================================
# For unhandled exceptions, add a generic handler that returns a 500 response with a generic message.
app.add_exception_handler(Exception, unhandled_exception_handler)

app.add_exception_handler(StarletteHTTPException, http_exception_handler)

# ======================================================================================================================
# Middleware (executed in reverse order of registration: last added = outermost)
# ======================================================================================================================
# Order of middleware execution:
#   - Incoming request: last to first (outermost to innermost)
#   - Outgoing response: first to last (innermost to outermost)

app.add_middleware(HeaderMiddleware)

app.add_middleware(ServerTimingsMiddleware)

app.add_middleware(JWTMiddleware)

app.add_middleware(LocalizationMiddleware)

app.add_middleware(GZipMiddleware, minimum_size=1000)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(TrustedHostMiddleware, allowed_hosts=ALLOWED_HOSTS)

# ======================================================================================================================
# Add routers for different API endpoints
# ======================================================================================================================
LOGGER.info("==== Registering Endpoints ".ljust(80, "="))

for endpoint_file in APP_SETTINGS.endpoints_root.rglob("*.py"):
    module_name_parts = endpoint_file.relative_to(APP_SETTINGS.project_root).with_suffix("").parts

    # Skip any modules that are meant to be private (start with an underscore).
    if any(part.startswith("_") for part in module_name_parts):
        continue

    module = import_module(".".join(module_name_parts))
    for name, obj in module.__dict__.items():
        # Check if the object is an instance of APIRouter and include it in the FastAPI application.
        if isinstance(obj, APIRouter):
            LOGGER.info("Adding APIRouter('%s') from module - %s", name, module.__name__)
            app.include_router(obj)
            break  # There is only one router per module, so we can stop after finding the first one.

LOGGER.info("=".ljust(80, "="))

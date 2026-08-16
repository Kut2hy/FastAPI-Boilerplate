"""FastAPI application entry point."""

from datetime import datetime, timezone
from typing import Annotated
from uuid import UUID

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from redis.asyncio import Redis
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.app_config import APP_SETTINGS
from app.common.exceptions import http_exception_handler, unhandled_exception_handler
from app.common.middleware.localization import LocalizationMiddleware
from app.core.jwt.access_token import ACCESS_TOKEN_COOKIE_KWARGS, AccessToken
from app.core.jwt.middleware import JWTMiddleware
from app.core.jwt.refresh_token import REFRESH_TOKEN_COOKIE_KWARGS, RefreshToken
from app.core.redis.dependencies import get_redis_client
from app.life_cycle import life_cycle
from app.piccolo.tables.refresh_token import add_refresh_token
from app.routes.account.v1.login import router as login_router
from app.routes.account.v1.logout import router as logout_router

app = FastAPI(
    title=APP_SETTINGS.title,
    version=APP_SETTINGS.version,
    lifespan=life_cycle,
    openapi_url="/openapi.json" if APP_SETTINGS.in_development else None,
    docs_url="/docs" if APP_SETTINGS.in_development else None,
    redoc_url="/redoc" if APP_SETTINGS.in_development else None,
)

ALLOWED_HOSTS = [str(APP_SETTINGS.host), f"{APP_SETTINGS.host}:{APP_SETTINGS.port}"]
"""Host header values accepted by the application."""

ALLOWED_ORIGINS = [f"http://{APP_SETTINGS.host}:{APP_SETTINGS.port}"]
"""Origins accepted by the CORS middleware."""

if APP_SETTINGS.public_host:
    ALLOWED_HOSTS.append(APP_SETTINGS.public_host)
    ALLOWED_ORIGINS.append(f"https://{APP_SETTINGS.public_host}")


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
app.add_middleware(JWTMiddleware)

app.add_middleware(LocalizationMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=ALLOWED_HOSTS,
)


app.include_router(login_router)
app.include_router(logout_router)


@app.get("/health-check/app")
async def health_check():
    return {"status": "ok"}


@app.get("/")
async def root(request: Request):
    return {"message": "Welcome to the FastAPI application!"}


@app.get("/health-check/pg")
async def health_check_pg():
    from piccolo.engine import engine_finder  # noqa: PLC0415
    from piccolo.engine.postgres import PostgresEngine  # noqa: PLC0415, TC002

    engine: PostgresEngine = engine_finder()  # type: ignore -> Only PG engine is used in this project

    result = await engine.run_ddl("SELECT 1;")

    return {"status": "ok" if result == [(1,)] else "error"}


@app.get("/health-check/redis")
async def health_check_redis(
    redis_client: Annotated[Redis, Depends(get_redis_client())],
):
    try:
        pong = await redis_client.ping()

    except Exception as e:
        return {"status": "error", "message": str(e)}

    else:
        return {"status": "ok" if pong else "error"}

"""FastAPI application entry point."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware

from app.app_config import APP_SETTINGS
from app.life_cycle import life_cycle

app = FastAPI(
    title=APP_SETTINGS.title,
    version=APP_SETTINGS.version,
    lifespan=life_cycle,
    openapi_url="/openapi.json" if APP_SETTINGS.in_development else None,
    docs_url="/docs" if APP_SETTINGS.in_development else None,
    redoc_url="/redoc" if APP_SETTINGS.in_development else None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[f"http://{APP_SETTINGS.host}:{APP_SETTINGS.port}"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=[str(APP_SETTINGS.host), f"{APP_SETTINGS.host}:{APP_SETTINGS.port}"],
)


@app.get("/health-check/app")
async def health_check():
    return {"status": "ok"}


@app.get("/health-check/pg")
async def health_check_pg():
    from piccolo.engine import engine_finder  # noqa: PLC0415
    from piccolo.engine.postgres import PostgresEngine  # noqa: PLC0415, TC002

    engine: PostgresEngine = engine_finder()  # type: ignore -> Only PG engine is used in this project

    result = await engine.run_ddl("SELECT 1;")

    return {"status": "ok" if result == [(1,)] else "error"}

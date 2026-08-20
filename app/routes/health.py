"""Health check endpoints for the application."""

from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from piccolo.engine import engine_finder
from piccolo.engine.postgres import PostgresEngine  # noqa: TC002
from redis.asyncio import Redis  # noqa: TC002 -> Needed for dependency

from app.core.redis.dependencies import get_redis_client

router = APIRouter(tags=["health"])

@router.get("/")
async def root() -> JSONResponse:
    """Root endpoint that verifies the application is running."""
    return JSONResponse(content={"message": "Welcome to the FastAPI application!"})


@router.get("/health/app")
async def health_check() -> JSONResponse:
    """App ping endpoint to check if the application is running."""
    return JSONResponse(content={"status": "ok"})


@router.get("/health/pg")
async def health_check_pg() -> JSONResponse:
    """PostgreSQL ping endpoint to check if the database is reachable."""
    engine: PostgresEngine = engine_finder()  # type: ignore -> Only PG engine is used in this project
    result = await engine.run_ddl("SELECT 1;")

    return JSONResponse(content={"status": "ok" if result == [(1,)] else "error"})


@router.get("/health/redis")
async def health_check_redis(
    redis_client: Annotated[Redis, Depends(get_redis_client())],
) -> JSONResponse:
    """Redis ping endpoint to check if the Redis server is reachable."""
    try:
        pong = await redis_client.ping()

    except Exception as e:
        return JSONResponse(content={"status": "error", "message": str(e)})

    else:
        return JSONResponse(content={"status": "ok" if pong else "error"})

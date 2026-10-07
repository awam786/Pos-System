from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.database import (
    check_database_connection,
    close_database,
    init_database,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifecycle.

    Database initialization and connection verification happen when the
    application starts. Cleanup happens during shutdown.
    """

    await init_database()

    database_ready = await check_database_connection()

    if not database_ready:
        raise RuntimeError(
            "PostgreSQL is unavailable. "
            "Check DATABASE_URL and database connectivity."
        )

    yield

    await close_database()


app = FastAPI(
    title=settings.app_name,
    description=(
        "Production-ready General Store Point of Sale system. "
        "The application intentionally does not implement a tax system."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", include_in_schema=False)
async def root():
    return {
        "name": settings.app_name,
        "version": "1.0.0",
        "status": "online",
        "environment": settings.app_env,
    }


@app.get("/health", tags=["System"])
async def health():
    database_ok = await check_database_connection()

    return {
        "status": "healthy" if database_ok else "degraded",
        "database": "connected" if database_ok else "unavailable",
        "environment": settings.app_env,
    }


@app.get("/api/health", tags=["System"])
async def api_health():
    database_ok = await check_database_connection()

    return {
        "status": "healthy" if database_ok else "degraded",
        "database": "connected" if database_ok else "unavailable",
        "application": settings.app_name,
    }


@app.exception_handler(Exception)
async def unhandled_exception_handler(request, exc):
    """
    Final safety net for unexpected exceptions.

    Detailed exception information is intentionally not exposed to clients.
    """

    if settings.debug:
        detail = str(exc)
    else:
        detail = "An unexpected server error occurred."

    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "message": detail,
        },
    )

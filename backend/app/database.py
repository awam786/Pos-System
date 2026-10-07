from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import settings


def normalize_database_url(url: str) -> str:
    """
    Normalize common PostgreSQL URLs supplied by Railway.

    Railway may provide:
        postgres://...
        postgresql://...

    SQLAlchemy async requires:
        postgresql+asyncpg://...
    """

    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://") :]

    if url.startswith("postgresql://"):
        url = "postgresql+asyncpg://" + url[len("postgresql://") :]

    return url


DATABASE_URL = normalize_database_url(settings.database_url)

engine: AsyncEngine = create_async_engine(
    DATABASE_URL,
    echo=settings.debug,
    pool_pre_ping=True,
    pool_recycle=1800,
    pool_size=10,
    max_overflow=20,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI database dependency.

    Every request receives its own SQLAlchemy async session.
    """

    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise


@asynccontextmanager
async def database_transaction():
    """
    Helper for service operations that require an explicit transaction.
    """

    async with AsyncSessionLocal() as session:
        async with session.begin():
            yield session


async def check_database_connection() -> bool:
    """
    Verify that PostgreSQL is reachable.
    """

    try:
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


async def init_database() -> None:
    """
    Initialize database metadata.

    The complete model registry will be imported once the model layer is
    installed. Keeping the import inside this function prevents circular
    imports during application startup.
    """

    from app.models import Base

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)


async def close_database() -> None:
    """
    Gracefully dispose of the connection pool.
    """

    await engine.dispose()

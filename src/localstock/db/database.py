"""Async SQLAlchemy engine and session factory for Supabase PostgreSQL."""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from localstock.config import get_settings


def get_engine():
    """Create async SQLAlchemy engine from settings."""
    settings = get_settings()
    return create_async_engine(
        settings.database_url,
        echo=False,
        pool_size=5,
        max_overflow=10,
    )


def get_session_factory(engine=None) -> async_sessionmaker[AsyncSession]:
    """Create async session factory."""
    if engine is None:
        engine = get_engine()
    return async_sessionmaker(engine, expire_on_commit=False)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency that yields an async database session."""
    factory = get_session_factory()
    async with factory() as session:
        yield session

"""Async SQLAlchemy engine and session factory for Supabase PostgreSQL."""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from localstock.config import get_settings

# Singleton engine and session factory — avoids creating duplicate connection pools
_engine = None
_session_factory = None


def get_engine():
    """Get or create the singleton async SQLAlchemy engine."""
    global _engine
    if _engine is None:
        settings = get_settings()
        _engine = create_async_engine(
            settings.database_url,
            echo=False,
            pool_size=3,
            max_overflow=5,
            pool_recycle=300,
            pool_pre_ping=True,
            connect_args={"prepared_statement_cache_size": 0, "statement_cache_size": 0},
        )
        # Phase 24-03 — DB query timing (OBS-12, OBS-13)
        from localstock.observability.db_events import attach_query_listener

        attach_query_listener(_engine)
    return _engine


def get_session_factory(engine=None) -> async_sessionmaker[AsyncSession]:
    """Get or create the singleton async session factory."""
    global _session_factory
    if engine is not None:
        return async_sessionmaker(engine, expire_on_commit=False)
    if _session_factory is None:
        _session_factory = async_sessionmaker(get_engine(), expire_on_commit=False)
    return _session_factory


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency that yields an async database session."""
    factory = get_session_factory()
    async with factory() as session:
        yield session

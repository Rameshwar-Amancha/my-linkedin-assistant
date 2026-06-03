"""
database.py — Async SQLAlchemy database setup with SQLite (default) or PostgreSQL.

Uses an abstraction layer so migrating from SQLite → PostgreSQL requires
only changing the DATABASE_URL environment variable.
"""

from __future__ import annotations

import logging

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config.settings import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------

def _build_engine_kwargs(url: str) -> dict:
    """Return engine kwargs appropriate for the database dialect."""
    is_sqlite = "sqlite" in url
    is_memory = ":memory:" in url

    kwargs: dict = {
        "echo": settings.DEBUG,
        "pool_pre_ping": True,
    }

    if is_sqlite:
        # SQLite needs check_same_thread disabled for async use
        kwargs["connect_args"] = {"check_same_thread": False}
        if is_memory:
            # In-memory SQLite: StaticPool keeps one reusable connection so all
            # sessions share the same in-memory database.  StaticPool does NOT
            # accept pool_size / max_overflow.
            from sqlalchemy.pool import StaticPool
            kwargs["poolclass"] = StaticPool
        else:
            # File-based SQLite: single writer to avoid WAL conflicts
            kwargs["pool_size"] = 1
            kwargs["max_overflow"] = 0
    else:
        # PostgreSQL / other — standard pool sizing
        kwargs["pool_size"] = 5
        kwargs["max_overflow"] = 10

    return kwargs


engine = create_async_engine(settings.DATABASE_URL, **_build_engine_kwargs(settings.DATABASE_URL))

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


# ---------------------------------------------------------------------------
# Base model
# ---------------------------------------------------------------------------

class Base(DeclarativeBase):
    pass


# ---------------------------------------------------------------------------
# Init
# ---------------------------------------------------------------------------

async def init_db() -> None:
    """Create all tables if they don't exist."""
    from app.models import orm  # noqa: F401 — ensures ORM models are registered

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Enable WAL mode for SQLite
    if "sqlite" in settings.DATABASE_URL:
        async with AsyncSessionLocal() as session:
            await session.execute(text("PRAGMA journal_mode=WAL"))
            await session.execute(text("PRAGMA foreign_keys=ON"))
            await session.commit()

    logger.info("Database tables verified/created.")


# ---------------------------------------------------------------------------
# Dependency
# ---------------------------------------------------------------------------

async def get_db() -> AsyncSession:  # type: ignore[override]
    """FastAPI dependency: yields a database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

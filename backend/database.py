"""
Database Infrastructure
Production-grade connection pooling, session management, and health checks.

Adapted from Ruflo pattern: infrastructure resilience + async session handling.
"""

import os
import logging
import asyncio
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional

from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncSession,
    async_sessionmaker,
    AsyncEngine,
)
from sqlalchemy.pool import NullPool
from sqlalchemy import text

# Re-export Base for compatibility with legacy code that imports it from database
from models import Base

logger = logging.getLogger(__name__)

# ── Configuration ─────────────────────────────────────────────────────────────
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@localhost:5432/agentverse"
)

# Pool settings for production
POOL_SIZE = int(os.getenv("DB_POOL_SIZE", "20"))
MAX_OVERFLOW = int(os.getenv("DB_MAX_OVERFLOW", "30"))
POOL_RECYCLE = int(os.getenv("DB_POOL_RECYCLE", "3600"))  # 1 hour
POOL_TIMEOUT = int(os.getenv("DB_POOL_TIMEOUT", "30"))
ECHO = os.getenv("DB_ECHO", "false").lower() == "true"

# ── Engine Factory ──────────────────────────────────────────────────────────
_engine: Optional[AsyncEngine] = None
_session_factory: Optional[async_sessionmaker[AsyncSession]] = None


def get_engine() -> AsyncEngine:
    """Get or create the async engine with connection pooling."""
    global _engine
    if _engine is None:
        if DATABASE_URL.startswith("sqlite"):
            # SQLite: no pool, single connection
            _engine = create_async_engine(
                DATABASE_URL,
                echo=ECHO,
                poolclass=NullPool,
            )
            logger.info("SQLite engine created (NullPool)")
        else:
            _engine = create_async_engine(
                DATABASE_URL,
                echo=ECHO,
                pool_size=POOL_SIZE,
                max_overflow=MAX_OVERFLOW,
                pool_recycle=POOL_RECYCLE,
                pool_timeout=POOL_TIMEOUT,
                pool_pre_ping=True,  # Health check before checkout
            )
            logger.info(
                "PostgreSQL engine created (pool_size=%d, max_overflow=%d, recycle=%ds)",
                POOL_SIZE, MAX_OVERFLOW, POOL_RECYCLE,
            )
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Get or create the async session factory."""
    global _session_factory
    if _session_factory is None:
        engine = get_engine()
        _session_factory = async_sessionmaker(
            engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
        )
    return _session_factory


async def close_engine() -> None:
    """Gracefully close the engine and all connections."""
    global _engine, _session_factory
    if _engine is not None:
        await _engine.dispose()
        _engine = None
        _session_factory = None
        logger.info("Database engine disposed")


# ── FastAPI Dependency ──────────────────────────────────────────────────────
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency: yields an async session, auto-rollback on error.
    Usage: db: AsyncSession = Depends(get_db)
    """
    factory = get_session_factory()
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# ── Context Manager ─────────────────────────────────────────────────────────
@asynccontextmanager
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Standalone context manager for DB sessions outside of FastAPI routes.
    Usage:
        async with db_session() as db:
            result = await db.execute(...)
    """
    factory = get_session_factory()
    session = factory()
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()


# ── Health Check ────────────────────────────────────────────────────────────
async def health_check() -> dict:
    """Check database connectivity and return pool stats."""
    engine = get_engine()
    try:
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT 1"))
            row = result.scalar()

        pool = engine.pool
        return {
            "status": "healthy" if row == 1 else "unhealthy",
            "pool_size": pool.size() if hasattr(pool, "size") else None,
            "checked_in": pool.checkedin() if hasattr(pool, "checkedin") else None,
            "checked_out": pool.checkedout() if hasattr(pool, "checkedout") else None,
            "overflow": pool.overflow() if hasattr(pool, "overflow") else None,
        }
    except Exception as e:
        logger.error("Database health check failed: %s", e)
        return {"status": "unhealthy", "error": str(e)}


# ── Migration Check ───────────────────────────────────────────────────────────
async def verify_migrations() -> bool:
    """Verify alembic_version table exists (migrations applied)."""
    engine = get_engine()
    try:
        async with engine.connect() as conn:
            result = await conn.execute(
                text("SELECT version_num FROM alembic_version LIMIT 1")
            )
            version = result.scalar()
            logger.info("Alembic version: %s", version)
            return True
    except Exception as e:
        logger.warning("Migration verification failed: %s", e)
        return False


# ── Table Initialization ────────────────────────────────────────────────────
async def init_db() -> None:
    """Create all tables if they don't exist."""
    from models import Base
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables initialized")


# ── Module-level exports for convenience ────────────────────────────────────
engine = get_engine()
AsyncSessionLocal = get_session_factory()

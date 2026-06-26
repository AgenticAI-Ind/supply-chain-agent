"""
Database configuration and connection management.

Provides PostgreSQL and Redis connection pools with proper lifecycle management,
connection pooling, and error handling for production use.
"""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional

import redis.asyncio as redis
from sqlalchemy import create_engine, MetaData, Table, Column, Integer, String, Float, DateTime, JSON, Boolean
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy.pool import NullPool, QueuePool

from .config import settings


logger = logging.getLogger(__name__)

# SQLAlchemy Base
Base = declarative_base()
metadata = MetaData()


# Database Tables
forecasts_table = Table(
    "forecasts",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("product_id", String(100), nullable=False, index=True),
    Column("forecast_date", DateTime, nullable=False, index=True),
    Column("predicted_value", Float, nullable=False),
    Column("lower_bound", Float),
    Column("upper_bound", Float),
    Column("confidence", Float),
    Column("model_version", String(50)),
    Column("created_at", DateTime, nullable=False),
    Column("metadata", JSON),
)

routes_table = Table(
    "routes",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("route_id", String(100), nullable=False, unique=True, index=True),
    Column("depot_id", String(100), nullable=False),
    Column("vehicle_id", Integer, nullable=False),
    Column("total_distance_km", Float, nullable=False),
    Column("total_time_minutes", Float, nullable=False),
    Column("total_cost", Float, nullable=False),
    Column("optimization_objective", String(50)),
    Column("created_at", DateTime, nullable=False),
    Column("route_data", JSON, nullable=False),
)

inventory_table = Table(
    "inventory",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("product_id", String(100), nullable=False, unique=True, index=True),
    Column("product_name", String(255), nullable=False),
    Column("sku", String(100), nullable=False, unique=True),
    Column("current_stock", Integer, nullable=False),
    Column("reorder_point", Integer),
    Column("safety_stock", Integer),
    Column("eoq", Integer),
    Column("unit_cost", Float, nullable=False),
    Column("holding_cost_percentage", Float),
    Column("ordering_cost", Float),
    Column("lead_time_days", Integer),
    Column("last_updated", DateTime, nullable=False),
    Column("metadata", JSON),
)

suppliers_table = Table(
    "suppliers",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("supplier_id", String(100), nullable=False, unique=True, index=True),
    Column("supplier_name", String(255), nullable=False),
    Column("country", String(100)),
    Column("overall_risk_score", Float),
    Column("risk_category", String(50)),
    Column("last_assessment_date", DateTime),
    Column("monitoring_frequency", String(50)),
    Column("is_active", Boolean, default=True),
    Column("metadata", JSON),
)

shipments_table = Table(
    "shipments",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("tracking_number", String(100), nullable=False, unique=True, index=True),
    Column("carrier", String(50), nullable=False),
    Column("current_status", String(50), nullable=False),
    Column("origin", String(255)),
    Column("destination", String(255)),
    Column("estimated_delivery", DateTime),
    Column("actual_delivery", DateTime),
    Column("last_updated", DateTime, nullable=False),
    Column("tracking_data", JSON),
)


class DatabaseManager:
    """Manages database connections and operations."""

    def __init__(self):
        """Initialize database manager."""
        self.engine: Optional[create_async_engine] = None
        self.session_factory: Optional[async_sessionmaker] = None
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize database connection pool."""
        if self._initialized:
            logger.warning("Database already initialized")
            return

        try:
            # Create async engine with connection pooling
            self.engine = create_async_engine(
                settings.DATABASE_URL,
                echo=settings.DEBUG,
                pool_size=settings.DB_POOL_SIZE,
                max_overflow=settings.DB_MAX_OVERFLOW,
                pool_pre_ping=True,
                pool_recycle=3600,
                poolclass=QueuePool if settings.DB_POOL_SIZE > 0 else NullPool,
            )

            # Create session factory
            self.session_factory = async_sessionmaker(
                self.engine,
                class_=AsyncSession,
                expire_on_commit=False,
            )

            # Create tables
            async with self.engine.begin() as conn:
                await conn.run_sync(metadata.create_all)

            self._initialized = True
            logger.info("Database initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise

    async def close(self) -> None:
        """Close database connections."""
        if self.engine:
            await self.engine.dispose()
            self._initialized = False
            logger.info("Database connections closed")

    @asynccontextmanager
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Get database session context manager."""
        if not self._initialized:
            await self.initialize()

        async with self.session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception as e:
                await session.rollback()
                logger.error(f"Database session error: {e}")
                raise
            finally:
                await session.close()


class RedisManager:
    """Manages Redis connections and operations."""

    def __init__(self):
        """Initialize Redis manager."""
        self.client: Optional[redis.Redis] = None
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize Redis connection pool."""
        if self._initialized:
            logger.warning("Redis already initialized")
            return

        try:
            self.client = await redis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True,
                max_connections=settings.REDIS_POOL_SIZE,
                socket_connect_timeout=5,
                socket_keepalive=True,
            )

            # Test connection
            await self.client.ping()

            self._initialized = True
            logger.info("Redis initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize Redis: {e}")
            raise

    async def close(self) -> None:
        """Close Redis connections."""
        if self.client:
            await self.client.close()
            self._initialized = False
            logger.info("Redis connections closed")

    async def get(self, key: str) -> Optional[str]:
        """Get value from Redis."""
        if not self._initialized:
            await self.initialize()

        try:
            return await self.client.get(key)
        except Exception as e:
            logger.error(f"Redis GET error for key {key}: {e}")
            return None

    async def set(
        self,
        key: str,
        value: str,
        expire: Optional[int] = None
    ) -> bool:
        """Set value in Redis with optional expiration."""
        if not self._initialized:
            await self.initialize()

        try:
            await self.client.set(key, value, ex=expire)
            return True
        except Exception as e:
            logger.error(f"Redis SET error for key {key}: {e}")
            return False

    async def delete(self, key: str) -> bool:
        """Delete key from Redis."""
        if not self._initialized:
            await self.initialize()

        try:
            await self.client.delete(key)
            return True
        except Exception as e:
            logger.error(f"Redis DELETE error for key {key}: {e}")
            return False

    async def exists(self, key: str) -> bool:
        """Check if key exists in Redis."""
        if not self._initialized:
            await self.initialize()

        try:
            return bool(await self.client.exists(key))
        except Exception as e:
            logger.error(f"Redis EXISTS error for key {key}: {e}")
            return False

    async def setex(self, key: str, seconds: int, value: str) -> bool:
        """Set key with expiration time."""
        return await self.set(key, value, expire=seconds)

    async def incr(self, key: str) -> Optional[int]:
        """Increment key value."""
        if not self._initialized:
            await self.initialize()

        try:
            return await self.client.incr(key)
        except Exception as e:
            logger.error(f"Redis INCR error for key {key}: {e}")
            return None

    async def expire(self, key: str, seconds: int) -> bool:
        """Set expiration time on key."""
        if not self._initialized:
            await self.initialize()

        try:
            return await self.client.expire(key, seconds)
        except Exception as e:
            logger.error(f"Redis EXPIRE error for key {key}: {e}")
            return False


# Global instances
db_manager = DatabaseManager()
redis_manager = RedisManager()


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency for database sessions."""
    async with db_manager.get_session() as session:
        yield session


async def get_redis_client() -> redis.Redis:
    """FastAPI dependency for Redis client."""
    if not redis_manager._initialized:
        await redis_manager.initialize()
    return redis_manager.client

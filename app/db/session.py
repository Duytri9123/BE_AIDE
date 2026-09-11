from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from typing import AsyncGenerator

from app.core.config import settings

from sqlalchemy import event

# Khởi tạo async engine với SQLite tuning (WAL mode, busy_timeout)
is_sqlite = "sqlite" in settings.DATABASE_ASYNC_URL.lower()
engine_kwargs = {
    "echo": settings.DB_ECHO,
}
if is_sqlite:
    engine_kwargs["connect_args"] = {"timeout": 60}
else:
    engine_kwargs["pool_pre_ping"] = True
    engine_kwargs["pool_size"] = 10
    engine_kwargs["max_overflow"] = 20

async_engine = create_async_engine(
    settings.DATABASE_ASYNC_URL,
    **engine_kwargs
)
engine = async_engine

if is_sqlite:
    @event.listens_for(async_engine.sync_engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA busy_timeout=60000")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.close()

# Khởi tạo session factory
AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    autocommit=False,
    autoflush=False,
    class_=AsyncSession,
    expire_on_commit=False,
)

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency để lấy database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

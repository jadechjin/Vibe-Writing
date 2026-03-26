import logging
from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings


class _SuppressTerminateCancelledError(logging.Filter):
    """Suppress 'Exception terminating connection' caused by CancelledError.

    When uvicorn cancels an ASGI task (client disconnect), the CancelledError
    propagates into SQLAlchemy's asyncpg connection cleanup. This is a known
    interaction issue that does not affect functionality.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        if record.exc_info and record.exc_info[1] is not None:
            if "CancelledError" in type(record.exc_info[1]).__name__:
                return False
        return True


# Apply filter to the exact logger SQLAlchemy's QueuePool uses
_pool_filter = _SuppressTerminateCancelledError()
logging.getLogger("sqlalchemy.pool.impl.QueuePool").addFilter(_pool_filter)
# Also cover AsyncAdaptedQueuePool and any other pool variants
logging.getLogger("sqlalchemy.pool.impl.AsyncAdaptedQueuePool").addFilter(_pool_filter)
logging.getLogger("sqlalchemy.pool.impl").addFilter(_pool_filter)

settings = get_settings()
engine = create_async_engine(
    settings.database_url,
    future=True,
    pool_pre_ping=True,
    pool_recycle=300,
    pool_size=5,
    max_overflow=10,
    pool_reset_on_return="rollback",
)
async_session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db_session() -> AsyncIterator[AsyncSession]:
    async with async_session_factory() as session:
        yield session

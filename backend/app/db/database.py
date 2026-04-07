import logging
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy.pool import AsyncAdaptedQueuePool
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.config import settings
from app.db.post_commit import pop_post_commit_hooks

logger = logging.getLogger(__name__)

# Pool configuration for serverless databases (Supabase/NeonDB)
DB_POOL_SIZE = 5
MAX_OVERFLOW = 10
POOL_RECYCLE = 300  # Recycle connections after 5 minutes
POOL_PRE_PING = True  # Check connection health before using

# Create the async engine with connection health checks
engine = create_async_engine(
    str(settings.ASYNC_DATABASE_URI),
    echo=False,
    poolclass=AsyncAdaptedQueuePool,
    pool_size=DB_POOL_SIZE,
    max_overflow=MAX_OVERFLOW,
    pool_recycle=POOL_RECYCLE,
    pool_pre_ping=POOL_PRE_PING,
)

# Create a sessionmaker factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that yields an async DB session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
            hooks = pop_post_commit_hooks(session)
            for hook in hooks:
                try:
                    await hook()
                except Exception:
                    logger.exception("Post-commit hook failed")
        except Exception:
            pop_post_commit_hooks(session)
            await session.rollback()
            raise
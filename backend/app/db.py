from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.config import settings

engine = create_async_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)


def get_session_maker() -> async_sessionmaker[AsyncSession]:
    return SessionLocal


def worker_session_maker() -> tuple[async_sessionmaker[AsyncSession], create_async_engine]:
    eng = create_async_engine(settings.database_url, poolclass=NullPool)
    return async_sessionmaker(eng, expire_on_commit=False), eng


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with SessionLocal() as session:
        yield session

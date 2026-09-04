from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager


class PostgresDatabase:
    """Optional production Postgres adapter. Imported lazily so local mode stays lightweight."""

    def __init__(self, database_url: str) -> None:
        try:
            from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
        except ImportError as exc:
            raise RuntimeError("Install the 'postgres' extra to use PostgresDatabase") from exc
        self.engine = create_async_engine(database_url, pool_pre_ping=True, pool_size=10, max_overflow=20)
        self._session_factory = async_sessionmaker(self.engine, expire_on_commit=False)

    @asynccontextmanager
    async def session(self) -> AsyncIterator[object]:
        async with self._session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    async def healthcheck(self) -> bool:
        from sqlalchemy import text

        async with self.engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
        return True

"""asyncpg connection pool, shared across the app."""
from __future__ import annotations

from pathlib import Path

import asyncpg

from backend.config import DATABASE_URL

SCHEMA_PATH = Path(__file__).resolve().parent / "schema.sql"

_pool: asyncpg.Pool | None = None


async def get_pool() -> asyncpg.Pool:
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(DATABASE_URL, min_size=1, max_size=10)
    return _pool


async def close_pool() -> None:
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None


async def apply_schema() -> None:
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(SCHEMA_PATH.read_text())

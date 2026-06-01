import asyncpg
from config import DATABASE_URL


async def create_pool() -> asyncpg.Pool:
    pool = await asyncpg.create_pool(DATABASE_URL)
    async with pool.acquire() as conn:
        await _init_schema(conn)
    return pool


async def _init_schema(conn: asyncpg.Connection) -> None:
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS guild_config (
            guild_id    BIGINT PRIMARY KEY,
            channel_id  BIGINT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS teams (
            id          SERIAL PRIMARY KEY,
            guild_id    BIGINT NOT NULL,
            name        TEXT   NOT NULL,
            UNIQUE (guild_id, name)
        );

        CREATE TABLE IF NOT EXISTS draft_picks (
            id               SERIAL PRIMARY KEY,
            guild_id         BIGINT NOT NULL,
            original_team_id INT    NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
            current_team_id  INT    NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
            season_year      INT    NOT NULL,
            round            INT    NOT NULL,
            CHECK (round BETWEEN 1 AND 10)
        );
    """)

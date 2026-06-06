import asyncpg
from config import DATABASE_URL


async def create_pool() -> asyncpg.Pool:
    pool = await asyncpg.create_pool(DATABASE_URL)
    async with pool.acquire() as conn:
        await _init_schema(conn)
    return pool


async def _init_schema(conn: asyncpg.Connection) -> None:
    # Core tables
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS guild_config (
            guild_id    BIGINT PRIMARY KEY,
            channel_id  BIGINT,            -- nullable: set via /setup, may not be configured yet
            rounds      INT NOT NULL DEFAULT 5,
            years_ahead INT NOT NULL DEFAULT 3
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
            CHECK (round BETWEEN 1 AND 20)
        );
    """)

    # Migrations: add new columns and relax constraints for existing installs
    await conn.execute("""
        ALTER TABLE guild_config
            ADD COLUMN IF NOT EXISTS rounds      INT NOT NULL DEFAULT 5;
        ALTER TABLE guild_config
            ADD COLUMN IF NOT EXISTS years_ahead INT NOT NULL DEFAULT 3;
        ALTER TABLE guild_config
            ALTER COLUMN channel_id DROP NOT NULL;
    """)

    # Add unique constraint to draft_picks if it doesn't already exist,
    # so bulk-insert helpers can use ON CONFLICT DO NOTHING safely.
    await conn.execute("""
        DO $$ BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conname = 'draft_picks_unique_pick'
            ) THEN
                ALTER TABLE draft_picks
                    ADD CONSTRAINT draft_picks_unique_pick
                    UNIQUE (guild_id, original_team_id, season_year, round);
            END IF;
        END $$;
    """)

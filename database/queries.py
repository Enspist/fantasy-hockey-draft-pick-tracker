import asyncpg

# ── Guild config ──────────────────────────────────────────────────────────────

async def set_channel(pool: asyncpg.Pool, guild_id: int, channel_id: int) -> None:
    await pool.execute("""
        INSERT INTO guild_config (guild_id, channel_id)
        VALUES ($1, $2)
        ON CONFLICT (guild_id) DO UPDATE SET channel_id = $2
    """, guild_id, channel_id)


async def get_channel(pool: asyncpg.Pool, guild_id: int) -> int | None:
    row = await pool.fetchrow(
        "SELECT channel_id FROM guild_config WHERE guild_id = $1", guild_id
    )
    return row["channel_id"] if row else None


# ── Teams ─────────────────────────────────────────────────────────────────────

async def add_team(pool: asyncpg.Pool, guild_id: int, name: str) -> int:
    row = await pool.fetchrow(
        "INSERT INTO teams (guild_id, name) VALUES ($1, $2) RETURNING id",
        guild_id, name,
    )
    return row["id"]


async def rename_team(pool: asyncpg.Pool, guild_id: int, old_name: str, new_name: str) -> bool:
    result = await pool.execute(
        "UPDATE teams SET name = $3 WHERE guild_id = $1 AND name = $2",
        guild_id, old_name, new_name,
    )
    return result != "UPDATE 0"


async def get_team(pool: asyncpg.Pool, guild_id: int, name: str) -> asyncpg.Record | None:
    return await pool.fetchrow(
        "SELECT * FROM teams WHERE guild_id = $1 AND name = $2", guild_id, name
    )


async def list_teams(pool: asyncpg.Pool, guild_id: int) -> list[asyncpg.Record]:
    return await pool.fetch(
        "SELECT * FROM teams WHERE guild_id = $1 ORDER BY name", guild_id
    )


async def delete_team(pool: asyncpg.Pool, guild_id: int, name: str) -> bool:
    result = await pool.execute(
        "DELETE FROM teams WHERE guild_id = $1 AND name = $2", guild_id, name
    )
    return result != "DELETE 0"


# ── Draft picks ───────────────────────────────────────────────────────────────

async def add_pick(
    pool: asyncpg.Pool,
    guild_id: int,
    original_team_id: int,
    season_year: int,
    round_num: int,
) -> int:
    row = await pool.fetchrow("""
        INSERT INTO draft_picks (guild_id, original_team_id, current_team_id, season_year, round)
        VALUES ($1, $2, $2, $3, $4)
        RETURNING id
    """, guild_id, original_team_id, season_year, round_num)
    return row["id"]


async def trade_pick(
    pool: asyncpg.Pool,
    guild_id: int,
    original_team_id: int,
    season_year: int,
    round_num: int,
    new_owner_id: int,
) -> bool:
    result = await pool.execute("""
        UPDATE draft_picks
        SET current_team_id = $5
        WHERE guild_id = $1
          AND original_team_id = $2
          AND season_year = $3
          AND round = $4
          AND current_team_id != $5
    """, guild_id, original_team_id, season_year, round_num, new_owner_id)
    return result != "UPDATE 0"


async def get_all_picks(pool: asyncpg.Pool, guild_id: int) -> list[asyncpg.Record]:
    """Return all picks with original and current team names."""
    return await pool.fetch("""
        SELECT
            dp.season_year,
            dp.round,
            orig.name  AS original_team,
            curr.name  AS current_team
        FROM draft_picks dp
        JOIN teams orig ON orig.id = dp.original_team_id
        JOIN teams curr ON curr.id = dp.current_team_id
        WHERE dp.guild_id = $1
        ORDER BY dp.season_year, dp.round, orig.name
    """, guild_id)


async def get_traded_picks(pool: asyncpg.Pool, guild_id: int) -> list[asyncpg.Record]:
    """Return only picks whose current owner differs from the original team."""
    return await pool.fetch("""
        SELECT
            dp.season_year,
            dp.round,
            orig.name AS original_team,
            curr.name AS current_team
        FROM draft_picks dp
        JOIN teams orig ON orig.id = dp.original_team_id
        JOIN teams curr ON curr.id = dp.current_team_id
        WHERE dp.guild_id = $1
          AND dp.original_team_id != dp.current_team_id
        ORDER BY dp.season_year, dp.round, orig.name
    """, guild_id)


async def delete_pick(
    pool: asyncpg.Pool,
    guild_id: int,
    original_team_id: int,
    season_year: int,
    round_num: int,
) -> bool:
    result = await pool.execute("""
        DELETE FROM draft_picks
        WHERE guild_id = $1
          AND original_team_id = $2
          AND season_year = $3
          AND round = $4
    """, guild_id, original_team_id, season_year, round_num)
    return result != "DELETE 0"

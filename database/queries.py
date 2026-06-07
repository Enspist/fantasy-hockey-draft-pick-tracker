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


async def get_settings(pool: asyncpg.Pool, guild_id: int) -> dict:
    """Return the league settings dict with defaults if not yet configured."""
    row = await pool.fetchrow(
        "SELECT rounds, years_ahead FROM guild_config WHERE guild_id = $1", guild_id
    )
    if row:
        return {"rounds": row["rounds"], "years_ahead": row["years_ahead"]}
    return {"rounds": 5, "years_ahead": 3}


async def set_rounds(pool: asyncpg.Pool, guild_id: int, rounds: int) -> None:
    await pool.execute("""
        INSERT INTO guild_config (guild_id, rounds)
        VALUES ($1, $2)
        ON CONFLICT (guild_id) DO UPDATE SET rounds = $2
    """, guild_id, rounds)


async def set_years_ahead(pool: asyncpg.Pool, guild_id: int, years_ahead: int) -> None:
    await pool.execute("""
        INSERT INTO guild_config (guild_id, years_ahead)
        VALUES ($1, $2)
        ON CONFLICT (guild_id) DO UPDATE SET years_ahead = $2
    """, guild_id, years_ahead)


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
) -> None:
    """Insert a pick. Silently skips if it already exists."""
    await pool.execute("""
        INSERT INTO draft_picks (guild_id, original_team_id, current_team_id, season_year, round)
        VALUES ($1, $2, $2, $3, $4)
        ON CONFLICT ON CONSTRAINT draft_picks_unique_pick DO NOTHING
    """, guild_id, original_team_id, season_year, round_num)


async def seed_picks_for_team(
    pool: asyncpg.Pool,
    guild_id: int,
    team_id: int,
    years: list[int],
    rounds: int,
) -> None:
    """
    Add one pick per round per year for a team.
    Skips any combination that already exists.
    """
    async with pool.acquire() as conn:
        async with conn.transaction():
            for year in years:
                for r in range(1, rounds + 1):
                    await conn.execute("""
                        INSERT INTO draft_picks
                            (guild_id, original_team_id, current_team_id, season_year, round)
                        VALUES ($1, $2, $2, $3, $4)
                        ON CONFLICT ON CONSTRAINT draft_picks_unique_pick DO NOTHING
                    """, guild_id, team_id, year, r)


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


async def get_pick_years_for_team(
    pool: asyncpg.Pool, guild_id: int, team_id: int
) -> list[int]:
    """Distinct years that have at least one pick originating from team_id."""
    rows = await pool.fetch("""
        SELECT DISTINCT season_year
        FROM draft_picks
        WHERE guild_id = $1 AND original_team_id = $2
        ORDER BY season_year
    """, guild_id, team_id)
    return [r["season_year"] for r in rows]


async def get_pick_rounds_for_team_year(
    pool: asyncpg.Pool, guild_id: int, team_id: int, year: int
) -> list[int]:
    """Rounds that exist for a given original_team + year."""
    rows = await pool.fetch("""
        SELECT round
        FROM draft_picks
        WHERE guild_id = $1 AND original_team_id = $2 AND season_year = $3
        ORDER BY round
    """, guild_id, team_id, year)
    return [r["round"] for r in rows]


# ── Current-holder lookups (for /pick trade) ──────────────────────────────────

async def get_years_team_holds(
    pool: asyncpg.Pool, guild_id: int, current_team_id: int
) -> list[int]:
    """Distinct years where the team CURRENTLY holds at least one pick."""
    rows = await pool.fetch("""
        SELECT DISTINCT season_year
        FROM draft_picks
        WHERE guild_id = $1 AND current_team_id = $2
        ORDER BY season_year
    """, guild_id, current_team_id)
    return [r["season_year"] for r in rows]


async def get_picks_team_holds(
    pool: asyncpg.Pool, guild_id: int, current_team_id: int, year: int
) -> list[asyncpg.Record]:
    """
    Picks the team CURRENTLY holds for a given year, including the original
    team's id and name (so the UI can show '3rd round (from Chytil)').
    """
    return await pool.fetch("""
        SELECT dp.round, dp.original_team_id, orig.name AS original_team
        FROM draft_picks dp
        JOIN teams orig ON orig.id = dp.original_team_id
        WHERE dp.guild_id = $1 AND dp.current_team_id = $2 AND dp.season_year = $3
        ORDER BY dp.round
    """, guild_id, current_team_id, year)


async def trade_pick_held(
    pool: asyncpg.Pool,
    guild_id: int,
    from_team_id: int,
    original_team_id: int,
    season_year: int,
    round_num: int,
    new_owner_id: int,
) -> bool:
    """
    Transfer a pick that from_team_id currently holds to new_owner_id.
    The pick is identified by (original_team_id, year, round) and guarded
    by current_team_id = from_team_id so you can only trade picks you hold.
    """
    result = await pool.execute("""
        UPDATE draft_picks
        SET current_team_id = $6
        WHERE guild_id = $1
          AND current_team_id = $2
          AND original_team_id = $3
          AND season_year = $4
          AND round = $5
    """, guild_id, from_team_id, original_team_id, season_year, round_num, new_owner_id)
    return result != "UPDATE 0"


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

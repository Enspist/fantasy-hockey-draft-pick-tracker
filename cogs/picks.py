from __future__ import annotations

from datetime import datetime

import discord
from discord import app_commands
from discord.ext import commands

from database import queries
from cogs.checks import has_admin_role

ORDINALS = {
    1: "1st", 2: "2nd", 3: "3rd", 4: "4th", 5: "5th",
    6: "6th", 7: "7th", 8: "8th", 9: "9th", 10: "10th",
}


def _round_label(r: int) -> str:
    return ORDINALS.get(r, f"R{r}")


# ── Table embed builder ───────────────────────────────────────────────────────

def _cell_content(team_name: str, year: int, picks: list) -> str:
    """
    Build the text for a single cell (team × year) using range compression.

    Consecutive own-picks collapse into a range:     1 2 3 4 5  →  1-5
    Traded picks show the original owner in parens:  R3 from Alpha  →  3(Alpha)
    Traded picks break ranges:  own 1,2 | traded 3 from Alpha | own 4,5  →  1-2 3(Alpha) 4-5
    Returns '-' if the team has no picks for that year.
    """
    team_picks = [
        p for p in picks
        if p["current_team"] == team_name and p["season_year"] == year
    ]
    if not team_picks:
        return "-"

    # List of (round, original_team_name) sorted by round
    items = sorted(
        [(p["round"], p["original_team"]) for p in team_picks],
        key=lambda x: x[0],
    )

    groups: list[str] = []
    i = 0
    while i < len(items):
        r, orig = items[i]
        is_traded = orig != team_name
        if is_traded:
            # Show round number and original owner — never merged into a range
            groups.append(f"{r}({orig})")
            i += 1
        else:
            # Extend a consecutive run of own-picks
            start = r
            end = r
            j = i + 1
            while j < len(items) and items[j][1] == team_name and items[j][0] == end + 1:
                end = items[j][0]
                j += 1
            groups.append(f"{start}-{end}" if end > start else str(start))
            i = j

    return " ".join(groups)


def _build_table(teams: list, picks: list, settings: dict) -> str:
    """
    Return a monospace table string:

        Team          | 2026        | 2027        | 2028
        --------------|-------------|-------------|-------------
        Alpha Wolves  | 1 2 3 4 5   | 1 2* 3 4 5  | 1 2 3 4 5
        Beta Bears    | 1 2 3 4 5   | 1 2 3 4 5   | 1 2 3 4 5

    * = acquired via trade
    """
    current_year = datetime.now().year
    years = list(range(current_year, current_year + settings["years_ahead"]))
    team_names = [t["name"] for t in teams]

    if not team_names:
        return "(No teams have been added yet.)"

    # Pre-compute all cell values
    cells: dict[str, dict[int, str]] = {
        name: {year: _cell_content(name, year, picks) for year in years}
        for name in team_names
    }

    # Column widths
    name_col_w = max((len(n) for n in team_names), default=4)
    name_col_w = max(name_col_w, len("Team"))

    year_col_w = {
        y: max(len(str(y)), max((len(cells[n][y]) for n in team_names), default=1))
        for y in years
    }

    # Header row
    header = "Team".ljust(name_col_w) + " | " + " | ".join(
        str(y).ljust(year_col_w[y]) for y in years
    )

    # Separator
    sep = "-" * name_col_w + "-+-" + "-+-".join(
        "-" * year_col_w[y] for y in years
    )

    # Data rows
    rows = [header, sep]
    for name in team_names:
        row = name.ljust(name_col_w) + " | " + " | ".join(
            cells[name][y].ljust(year_col_w[y]) for y in years
        )
        rows.append(row)

    return "\n".join(rows)


def _build_embed(teams: list, picks: list, settings: dict) -> discord.Embed:
    embed = discord.Embed(
        title="🏒 Fantasy Hockey Draft Pick Board",
        color=discord.Color.blue(),
    )

    table = _build_table(teams, picks, settings)
    embed.description = f"```\n{table}\n```"


    return embed


# ── Board poster ──────────────────────────────────────────────────────────────

async def post_pick_board(bot: commands.Bot, guild_id: int) -> None:
    channel_id = await queries.get_channel(bot.pool, guild_id)
    if not channel_id:
        return

    channel = bot.get_channel(channel_id)
    if not isinstance(channel, discord.TextChannel):
        return

    teams    = await queries.list_teams(bot.pool, guild_id)
    picks    = await queries.get_all_picks(bot.pool, guild_id)
    settings = await queries.get_settings(bot.pool, guild_id)
    embed    = _build_embed(teams, picks, settings)

    # Edit the existing board message rather than posting a new one
    async for msg in channel.history(limit=50):
        if msg.author == bot.user and msg.embeds and "Draft Pick Board" in msg.embeds[0].title:
            await msg.edit(embed=embed)
            return

    await channel.send(embed=embed)


# ── Cog ───────────────────────────────────────────────────────────────────────

class Picks(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    pick = app_commands.Group(name="pick", description="Manage draft picks.")

    @pick.command(name="add", description="Add a draft pick to a team's original holdings.")
    @app_commands.describe(
        team="Team that originally owns this pick.",
        year="Draft year (e.g. 2026).",
        round="Round number (1–20).",
    )
    @has_admin_role()
    async def pick_add(
        self,
        interaction: discord.Interaction,
        team: str,
        year: int,
        round: app_commands.Range[int, 1, 20],
    ) -> None:
        team_row = await queries.get_team(self.bot.pool, interaction.guild_id, team)
        if not team_row:
            await interaction.response.send_message(f"Team **{team}** not found.", ephemeral=True)
            return

        await queries.add_pick(self.bot.pool, interaction.guild_id, team_row["id"], year, round)
        await interaction.response.send_message(
            f"Added {year} {_round_label(round)} round pick for **{team}**.", ephemeral=True
        )
        await post_pick_board(self.bot, interaction.guild_id)

    @pick.command(name="trade", description="Record a draft pick trade between two teams.")
    @app_commands.describe(
        original_team="Team that originally owned the pick.",
        year="Draft year of the pick.",
        round="Round number (1–20).",
        new_owner="Team receiving the pick.",
    )
    @has_admin_role()
    async def pick_trade(
        self,
        interaction: discord.Interaction,
        original_team: str,
        year: int,
        round: app_commands.Range[int, 1, 20],
        new_owner: str,
    ) -> None:
        guild_id = interaction.guild_id

        orig_row = await queries.get_team(self.bot.pool, guild_id, original_team)
        if not orig_row:
            await interaction.response.send_message(f"Team **{original_team}** not found.", ephemeral=True)
            return

        new_row = await queries.get_team(self.bot.pool, guild_id, new_owner)
        if not new_row:
            await interaction.response.send_message(f"Team **{new_owner}** not found.", ephemeral=True)
            return

        updated = await queries.trade_pick(
            self.bot.pool, guild_id, orig_row["id"], year, round, new_row["id"]
        )
        if not updated:
            await interaction.response.send_message(
                f"Could not find that pick or it already belongs to **{new_owner}**.", ephemeral=True
            )
            return

        await interaction.response.send_message(
            f"Traded {year} {_round_label(round)} pick from **{original_team}** → **{new_owner}**.",
            ephemeral=True,
        )
        await post_pick_board(self.bot, interaction.guild_id)

    @pick.command(name="remove", description="Remove a draft pick entirely.")
    @app_commands.describe(
        original_team="Team that originally owned the pick.",
        year="Draft year.",
        round="Round number (1–20).",
    )
    @has_admin_role()
    async def pick_remove(
        self,
        interaction: discord.Interaction,
        original_team: str,
        year: int,
        round: app_commands.Range[int, 1, 20],
    ) -> None:
        orig_row = await queries.get_team(self.bot.pool, interaction.guild_id, original_team)
        if not orig_row:
            await interaction.response.send_message(f"Team **{original_team}** not found.", ephemeral=True)
            return

        deleted = await queries.delete_pick(
            self.bot.pool, interaction.guild_id, orig_row["id"], year, round
        )
        if not deleted:
            await interaction.response.send_message("Pick not found.", ephemeral=True)
            return

        await interaction.response.send_message(
            f"Removed {year} {_round_label(round)} pick (originally **{original_team}**).", ephemeral=True
        )
        await post_pick_board(self.bot, interaction.guild_id)

    @pick.command(name="refresh", description="Re-post the draft pick board to the configured channel.")
    async def pick_refresh(self, interaction: discord.Interaction) -> None:
        await interaction.response.send_message("Refreshing pick board…", ephemeral=True)
        await post_pick_board(self.bot, interaction.guild_id)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Picks(bot))

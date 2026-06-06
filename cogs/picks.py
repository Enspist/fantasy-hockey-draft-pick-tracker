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
    return ORDINALS.get(r, f"{r}th")


# ── Table embed builder ───────────────────────────────────────────────────────

def _cell_content(team_name: str, year: int, picks: list) -> str:
    """
    Build the text for a single cell (team × year) using range compression.

    Consecutive own-picks collapse into a range:     1 2 3 4 5  →  1-5
    Traded picks show the original owner in parens:  R3 from Alpha  →  3(Alpha)
    Traded picks break ranges:  own 1,2 | traded 3 | own 4,5  →  1-2 3(Alpha) 4-5
    Returns '-' if the team has no picks for that year.
    """
    team_picks = [
        p for p in picks
        if p["current_team"] == team_name and p["season_year"] == year
    ]
    if not team_picks:
        return "-"

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
            groups.append(f"{r}({orig})")
            i += 1
        else:
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
    current_year = datetime.now().year
    years = list(range(current_year, current_year + settings["years_ahead"]))
    team_names = [t["name"] for t in teams]

    if not team_names:
        return "(No teams have been added yet.)"

    cells: dict[str, dict[int, str]] = {
        name: {year: _cell_content(name, year, picks) for year in years}
        for name in team_names
    }

    name_col_w = max((len(n) for n in team_names), default=4)
    name_col_w = max(name_col_w, len("Team"))

    year_col_w = {
        y: max(len(str(y)), max((len(cells[n][y]) for n in team_names), default=1))
        for y in years
    }

    header = "Team".ljust(name_col_w) + " | " + " | ".join(
        str(y).ljust(year_col_w[y]) for y in years
    )
    sep = "-" * name_col_w + "-+-" + "-+-".join("-" * year_col_w[y] for y in years)

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

    # ── /pick add ─────────────────────────────────────────────────────────────

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

    # ── /pick trade ───────────────────────────────────────────────────────────

    @pick.command(name="trade", description="Record a draft pick trade between two teams.")
    @app_commands.describe(
        original_team="Team that originally owned the pick.",
        year="Draft year of the pick.",
        round="Round of the pick.",
        new_owner="Team receiving the pick.",
    )
    @has_admin_role()
    async def pick_trade(
        self,
        interaction: discord.Interaction,
        original_team: str,
        year: int,
        round: int,
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
            f"Traded {year} {_round_label(round)} pick (originally **{original_team}**) → **{new_owner}**.",
            ephemeral=True,
        )
        await post_pick_board(self.bot, interaction.guild_id)

    # Autocomplete: original_team — all teams in the guild
    @pick_trade.autocomplete("original_team")
    async def _ac_original_team(
        self, interaction: discord.Interaction, current: str
    ) -> list[app_commands.Choice[str]]:
        teams = await queries.list_teams(self.bot.pool, interaction.guild_id)
        return [
            app_commands.Choice(name=t["name"], value=t["name"])
            for t in teams
            if current.lower() in t["name"].lower()
        ][:25]

    # Autocomplete: year — years that have picks for the chosen original_team
    @pick_trade.autocomplete("year")
    async def _ac_year(
        self, interaction: discord.Interaction, current: str
    ) -> list[app_commands.Choice[int]]:
        team_name = interaction.namespace.original_team
        if not team_name:
            return []
        team = await queries.get_team(self.bot.pool, interaction.guild_id, team_name)
        if not team:
            return []
        years = await queries.get_pick_years_for_team(
            self.bot.pool, interaction.guild_id, team["id"]
        )
        return [
            app_commands.Choice(name=str(y), value=y)
            for y in years
            if not current or current in str(y)
        ][:25]

    # Autocomplete: round — rounds that exist for chosen original_team + year
    @pick_trade.autocomplete("round")
    async def _ac_round(
        self, interaction: discord.Interaction, current: str
    ) -> list[app_commands.Choice[int]]:
        team_name = interaction.namespace.original_team
        raw_year  = interaction.namespace.year
        if not team_name or not raw_year:
            return []
        try:
            year = int(raw_year)
        except (TypeError, ValueError):
            return []
        team = await queries.get_team(self.bot.pool, interaction.guild_id, team_name)
        if not team:
            return []
        rounds = await queries.get_pick_rounds_for_team_year(
            self.bot.pool, interaction.guild_id, team["id"], year
        )
        return [
            app_commands.Choice(name=_round_label(r), value=r)
            for r in rounds
            if not current or current in str(r)
        ][:25]

    # Autocomplete: new_owner — all teams except the original_team
    @pick_trade.autocomplete("new_owner")
    async def _ac_new_owner(
        self, interaction: discord.Interaction, current: str
    ) -> list[app_commands.Choice[str]]:
        teams = await queries.list_teams(self.bot.pool, interaction.guild_id)
        original = interaction.namespace.original_team or ""
        return [
            app_commands.Choice(name=t["name"], value=t["name"])
            for t in teams
            if t["name"] != original and current.lower() in t["name"].lower()
        ][:25]

    # ── /pick remove ──────────────────────────────────────────────────────────

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

    # ── /pick refresh ─────────────────────────────────────────────────────────

    @pick.command(name="refresh", description="Re-post the draft pick board to the configured channel.")
    async def pick_refresh(self, interaction: discord.Interaction) -> None:
        await interaction.response.send_message("Refreshing pick board…", ephemeral=True)
        await post_pick_board(self.bot, interaction.guild_id)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Picks(bot))

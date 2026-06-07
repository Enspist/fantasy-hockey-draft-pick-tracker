from __future__ import annotations

from datetime import datetime

import discord
from discord import app_commands
from discord.ext import commands

from config import REPLY_DELETE_AFTER
from database import queries
from cogs.checks import has_admin_role

ORDINALS = {
    1: "1st", 2: "2nd", 3: "3rd", 4: "4th", 5: "5th",
    6: "6th", 7: "7th", 8: "8th", 9: "9th", 10: "10th",
}


def _round_label(r: int) -> str:
    return ORDINALS.get(r, f"{r}th")


# ── Per-year embed builder ────────────────────────────────────────────────────

def _year_embed_title(year: int) -> str:
    return f"🏒 {year} Draft Picks"


def _cell_content(team_name: str, year: int, picks: list) -> str:
    """
    Picks for one team in one year, using range compression.

    Consecutive own-picks collapse (1 2 3 4 5 → 1-5).
    Traded picks show the original owner (3(Alpha)) and break ranges.
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
        if orig != team_name:
            groups.append(f"{r}({orig})")
            i += 1
        else:
            start, end = r, r
            j = i + 1
            while j < len(items) and items[j][1] == team_name and items[j][0] == end + 1:
                end = items[j][0]
                j += 1
            groups.append(f"{start}-{end}" if end > start else str(start))
            i = j

    return " ".join(groups)


def _build_year_embed(year: int, teams: list, picks: list) -> discord.Embed:
    """
    Build the embed for a single year using two inline fields:
      Team  | Picks

    Inline fields render side-by-side on all clients, so Team and Picks
    always sit on one line with no code-block wrapping issues.
    """
    embed = discord.Embed(
        title=_year_embed_title(year),
        color=discord.Color.blue(),
    )

    team_names = [t["name"] for t in teams]
    if not team_names:
        embed.description = "*(No teams have been added yet.)*"
        return embed

    team_col  = "\n".join(team_names)
    picks_col = "\n".join(_cell_content(name, year, picks) for name in team_names)

    embed.add_field(name="Team",  value=team_col,  inline=True)
    embed.add_field(name="Picks", value=picks_col, inline=True)

    return embed


# ── Board poster ──────────────────────────────────────────────────────────────

def _is_board_message(msg: discord.Message, bot_user: discord.ClientUser) -> bool:
    """True if msg is one of the bot's draft-pick board embeds."""
    return (
        msg.author == bot_user
        and bool(msg.embeds)
        and bool(msg.embeds[0].title)
        and msg.embeds[0].title.endswith("Draft Picks")
    )


async def post_pick_board(bot: commands.Bot, guild_id: int, *, purge: bool = False) -> None:
    """
    Post or update one message per tracked year in the configured channel.
    Years are processed in ascending order so new posts appear chronologically.

    If purge=True, delete all existing board messages first and post fresh
    ones (used by /pick refresh).  Otherwise existing year messages are
    edited in place and any missing years are appended.
    """
    channel_id = await queries.get_channel(bot.pool, guild_id)
    if not channel_id:
        return
    channel = bot.get_channel(channel_id)
    if not isinstance(channel, discord.TextChannel):
        return

    teams    = await queries.list_teams(bot.pool, guild_id)
    picks    = await queries.get_all_picks(bot.pool, guild_id)
    settings = await queries.get_settings(bot.pool, guild_id)

    current_year = datetime.now().year
    years        = list(range(current_year, current_year + settings["years_ahead"]))

    if purge:
        # Delete every existing board message, then repost all years fresh
        async for msg in channel.history(limit=200):
            if _is_board_message(msg, bot.user):
                await msg.delete()
        for year in years:
            await channel.send(embed=_build_year_embed(year, teams, picks))
        return

    # Map existing year messages by title so we can edit in place
    existing: dict[str, discord.Message] = {}
    async for msg in channel.history(limit=200):
        if _is_board_message(msg, bot.user):
            existing[msg.embeds[0].title] = msg

    for year in years:
        embed = _build_year_embed(year, teams, picks)
        title = _year_embed_title(year)
        if title in existing:
            await existing[title].edit(embed=embed)
        else:
            await channel.send(embed=embed)


# ── Autocomplete callbacks (module-level for reliable binding) ────────────────
# /pick trade works from the CURRENT HOLDER's perspective:
#   team   → the team trading the pick away (current holder)
#   year   → years where that team currently holds picks
#   pick   → the specific pick they hold, labelled with its origin.
#            value encodes "<original_team_id>:<round>" so duplicates
#            (own R3 + an acquired R3) are distinguishable.
#   new_owner → the team receiving the pick.

async def _ac_from_team(
    interaction: discord.Interaction, current: str
) -> list[app_commands.Choice[str]]:
    teams = await queries.list_teams(interaction.client.pool, interaction.guild_id)
    return [
        app_commands.Choice(name=t["name"], value=t["name"])
        for t in teams
        if current.lower() in t["name"].lower()
    ][:25]


async def _ac_year(
    interaction: discord.Interaction, current: str
) -> list[app_commands.Choice[int]]:
    pool      = interaction.client.pool
    team_name = interaction.namespace.team
    if not team_name:
        return []
    team = await queries.get_team(pool, interaction.guild_id, team_name)
    if not team:
        return []
    years = await queries.get_years_team_holds(pool, interaction.guild_id, team["id"])
    return [
        app_commands.Choice(name=str(y), value=y)
        for y in years
        if not current or current in str(y)
    ][:25]


async def _ac_pick(
    interaction: discord.Interaction, current: str
) -> list[app_commands.Choice[str]]:
    pool      = interaction.client.pool
    team_name = interaction.namespace.team
    raw_year  = interaction.namespace.year
    if not team_name or raw_year is None:
        return []
    try:
        year = int(raw_year)
    except (TypeError, ValueError):
        return []
    team = await queries.get_team(pool, interaction.guild_id, team_name)
    if not team:
        return []

    held = await queries.get_picks_team_holds(pool, interaction.guild_id, team["id"], year)
    choices: list[app_commands.Choice[str]] = []
    for p in held:
        if p["original_team"] == team_name:
            label = f"{_round_label(p['round'])} round (own)"
        else:
            label = f"{_round_label(p['round'])} round (from {p['original_team']})"
        if current and current.lower() not in label.lower():
            continue
        # value encodes original_team_id:round so the command can find the exact pick
        choices.append(app_commands.Choice(name=label, value=f"{p['original_team_id']}:{p['round']}"))
    return choices[:25]


async def _ac_new_owner(
    interaction: discord.Interaction, current: str
) -> list[app_commands.Choice[str]]:
    pool      = interaction.client.pool
    teams     = await queries.list_teams(pool, interaction.guild_id)
    from_team = interaction.namespace.team or ""
    return [
        app_commands.Choice(name=t["name"], value=t["name"])
        for t in teams
        if t["name"] != from_team and current.lower() in t["name"].lower()
    ][:25]


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
            await interaction.response.send_message(
                f"Team **{team}** not found.", ephemeral=True, delete_after=REPLY_DELETE_AFTER
            )
            return
        await queries.add_pick(self.bot.pool, interaction.guild_id, team_row["id"], year, round)
        await interaction.response.send_message(
            f"Added {year} {_round_label(round)} round pick for **{team}**.",
            ephemeral=True, delete_after=REPLY_DELETE_AFTER,
        )
        await post_pick_board(self.bot, interaction.guild_id)

    # ── /pick trade ───────────────────────────────────────────────────────────

    @pick.command(name="trade", description="Record a draft pick trade between two teams.")
    @app_commands.describe(
        team="Team trading the pick away (the team that currently holds it).",
        year="Draft year — options populate after selecting a team.",
        pick="The pick to trade — options populate after selecting a team and year.",
        new_owner="Team receiving the pick.",
    )
    @app_commands.autocomplete(
        team=_ac_from_team,
        year=_ac_year,
        pick=_ac_pick,
        new_owner=_ac_new_owner,
    )
    @has_admin_role()
    async def pick_trade(
        self,
        interaction: discord.Interaction,
        team: str,
        year: int,
        pick: str,
        new_owner: str,
    ) -> None:
        guild_id = interaction.guild_id

        from_row = await queries.get_team(self.bot.pool, guild_id, team)
        if not from_row:
            await interaction.response.send_message(
                f"Team **{team}** not found.", ephemeral=True, delete_after=REPLY_DELETE_AFTER
            )
            return
        new_row = await queries.get_team(self.bot.pool, guild_id, new_owner)
        if not new_row:
            await interaction.response.send_message(
                f"Team **{new_owner}** not found.", ephemeral=True, delete_after=REPLY_DELETE_AFTER
            )
            return

        # pick value is "<original_team_id>:<round>" from the autocomplete
        try:
            original_team_id_str, round_str = pick.split(":")
            original_team_id = int(original_team_id_str)
            round_num = int(round_str)
        except (ValueError, AttributeError):
            await interaction.response.send_message(
                "Invalid pick — please select one from the autocomplete list.",
                ephemeral=True, delete_after=REPLY_DELETE_AFTER,
            )
            return

        updated = await queries.trade_pick_held(
            self.bot.pool, guild_id, from_row["id"], original_team_id, year, round_num, new_row["id"]
        )
        if not updated:
            await interaction.response.send_message(
                f"Could not find that pick held by **{team}** (it may have already been traded).",
                ephemeral=True, delete_after=REPLY_DELETE_AFTER,
            )
            return

        await interaction.response.send_message(
            f"Traded {year} {_round_label(round_num)} round pick from **{team}** → **{new_owner}**.",
            ephemeral=True, delete_after=REPLY_DELETE_AFTER,
        )
        await post_pick_board(self.bot, interaction.guild_id)

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
            await interaction.response.send_message(
                f"Team **{original_team}** not found.", ephemeral=True, delete_after=REPLY_DELETE_AFTER
            )
            return
        deleted = await queries.delete_pick(
            self.bot.pool, interaction.guild_id, orig_row["id"], year, round
        )
        if not deleted:
            await interaction.response.send_message(
                "Pick not found.", ephemeral=True, delete_after=REPLY_DELETE_AFTER
            )
            return
        await interaction.response.send_message(
            f"Removed {year} {_round_label(round)} pick (originally **{original_team}**).",
            ephemeral=True, delete_after=REPLY_DELETE_AFTER,
        )
        await post_pick_board(self.bot, interaction.guild_id)

    # ── /pick refresh ─────────────────────────────────────────────────────────

    @pick.command(
        name="refresh",
        description="Delete and re-post all year boards (clears out any stale messages).",
    )
    async def pick_refresh(self, interaction: discord.Interaction) -> None:
        await interaction.response.send_message(
            "Refreshing pick boards…", ephemeral=True, delete_after=REPLY_DELETE_AFTER
        )
        await post_pick_board(self.bot, interaction.guild_id, purge=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Picks(bot))

    # Attach autocomplete callbacks directly to the Command objects that are
    # now live in the tree.  The Cog metaclass copies commands during injection
    # and does not reliably carry over _autocomplete_callbacks set by the
    # @app_commands.autocomplete() class-body decorator, so we register them
    # here — after add_cog() — on the actual objects Discord will sync.
    import logging
    log = logging.getLogger(__name__)

    pick_group = bot.tree.get_command("pick")
    if pick_group is None:
        log.error("Autocomplete setup: 'pick' group not found in tree.")
        return

    trade_cmd = pick_group.get_command("trade")
    if trade_cmd is None:
        log.error("Autocomplete setup: 'pick trade' command not found in tree.")
        return

    trade_cmd.autocomplete("team")(_ac_from_team)
    trade_cmd.autocomplete("year")(_ac_year)
    trade_cmd.autocomplete("pick")(_ac_pick)
    trade_cmd.autocomplete("new_owner")(_ac_new_owner)
    log.info("Autocomplete callbacks registered on 'pick trade'.")

from __future__ import annotations

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


def _build_embed(teams: list, picks: list[dict]) -> discord.Embed:
    embed = discord.Embed(
        title="Fantasy Hockey Draft Pick Board",
        color=discord.Color.blue(),
    )

    picks_by_owner: dict[str, list] = {t["name"]: [] for t in teams}

    for p in picks:
        owner = p["current_team"]
        if owner not in picks_by_owner:
            picks_by_owner[owner] = []
        picks_by_owner[owner].append(p)

    for team_name, team_picks in sorted(picks_by_owner.items()):
        if not team_picks:
            embed.add_field(name=team_name, value="*(no picks)*", inline=False)
            continue

        lines: list[str] = []
        for p in sorted(team_picks, key=lambda x: (x["season_year"], x["round"])):
            label = f"{p['season_year']} {_round_label(p['round'])}"
            if p["original_team"] != p["current_team"]:
                label += f" *(from {p['original_team']})*"
            lines.append(f"• {label}")

        embed.add_field(name=team_name, value="\n".join(lines), inline=False)

    if not any(v for v in picks_by_owner.values()):
        embed.description = "No draft picks have been entered yet."

    return embed


async def post_pick_board(bot: commands.Bot, guild_id: int) -> None:
    channel_id = await queries.get_channel(bot.pool, guild_id)
    if not channel_id:
        return

    channel = bot.get_channel(channel_id)
    if not isinstance(channel, discord.TextChannel):
        return

    teams = await queries.list_teams(bot.pool, guild_id)
    picks = await queries.get_all_picks(bot.pool, guild_id)
    embed = _build_embed(teams, picks)

    # Replace the most recent bot board message instead of spamming
    async for msg in channel.history(limit=50):
        if msg.author == bot.user and msg.embeds and msg.embeds[0].title == embed.title:
            await msg.edit(embed=embed)
            return

    await channel.send(embed=embed)


class Picks(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    pick = app_commands.Group(name="pick", description="Manage draft picks.")

    @pick.command(name="add", description="Add a draft pick to a team's original holdings.")
    @app_commands.describe(
        team="Team that originally owns this pick.",
        year="Draft year (e.g. 2026).",
        round="Round number (1–10).",
    )
    @has_admin_role()
    async def pick_add(
        self,
        interaction: discord.Interaction,
        team: str,
        year: int,
        round: app_commands.Range[int, 1, 10],
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
        round="Round number (1–10).",
        new_owner="Team receiving the pick.",
    )
    @has_admin_role()
    async def pick_trade(
        self,
        interaction: discord.Interaction,
        original_team: str,
        year: int,
        round: app_commands.Range[int, 1, 10],
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
        round="Round number (1–10).",
    )
    @has_admin_role()
    async def pick_remove(
        self,
        interaction: discord.Interaction,
        original_team: str,
        year: int,
        round: app_commands.Range[int, 1, 10],
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
        await interaction.response.send_message("Refreshing pick board...", ephemeral=True)
        await post_pick_board(self.bot, interaction.guild_id)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Picks(bot))

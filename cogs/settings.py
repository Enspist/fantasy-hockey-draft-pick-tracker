from __future__ import annotations

from datetime import datetime

import discord
from discord import app_commands
from discord.ext import commands

from config import REPLY_DELETE_AFTER
from database import queries
from cogs.checks import has_admin_role
from cogs.picks import post_pick_board


class Settings(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    rounds_group = app_commands.Group(name="rounds", description="Configure the number of draft rounds.")

    @rounds_group.command(name="set", description="Set the number of rounds in the draft.")
    @app_commands.describe(number="How many rounds the draft has (1–20).")
    @has_admin_role()
    async def rounds_set(
        self,
        interaction: discord.Interaction,
        number: app_commands.Range[int, 1, 20],
    ) -> None:
        guild_id = interaction.guild_id
        await queries.set_rounds(self.bot.pool, guild_id, number)

        settings     = await queries.get_settings(self.bot.pool, guild_id)
        current_year = datetime.now().year
        years        = list(range(current_year, current_year + settings["years_ahead"]))
        teams        = await queries.list_teams(self.bot.pool, guild_id)
        for team in teams:
            await queries.seed_picks_for_team(self.bot.pool, guild_id, team["id"], years, number)

        await interaction.response.send_message(
            f"Draft set to **{number} rounds**. All teams seeded for rounds 1–{number} across {len(years)} year(s).",
            ephemeral=True, delete_after=REPLY_DELETE_AFTER,
        )
        await post_pick_board(self.bot, guild_id)

    @rounds_group.command(name="show", description="Show the current number of draft rounds.")
    async def rounds_show(self, interaction: discord.Interaction) -> None:
        settings = await queries.get_settings(self.bot.pool, interaction.guild_id)
        await interaction.response.send_message(
            f"The draft is currently set to **{settings['rounds']} rounds**.",
            ephemeral=True, delete_after=REPLY_DELETE_AFTER,
        )

    years_group = app_commands.Group(name="years", description="Configure how many future years of picks are tracked.")

    @years_group.command(name="set", description="Set how many years of picks are tracked.")
    @app_commands.describe(number="Number of years ahead to track (1–10). Starts from the current calendar year.")
    @has_admin_role()
    async def years_set(
        self,
        interaction: discord.Interaction,
        number: app_commands.Range[int, 1, 10],
    ) -> None:
        guild_id = interaction.guild_id
        await queries.set_years_ahead(self.bot.pool, guild_id, number)

        settings     = await queries.get_settings(self.bot.pool, guild_id)
        current_year = datetime.now().year
        years        = list(range(current_year, current_year + number))
        teams        = await queries.list_teams(self.bot.pool, guild_id)
        for team in teams:
            await queries.seed_picks_for_team(self.bot.pool, guild_id, team["id"], years, settings["rounds"])

        year_range = f"{current_year}–{current_year + number - 1}" if number > 1 else str(current_year)
        await interaction.response.send_message(
            f"Now tracking **{number} year(s)** of picks ({year_range}). All teams seeded for the full range.",
            ephemeral=True, delete_after=REPLY_DELETE_AFTER,
        )
        await post_pick_board(self.bot, guild_id)

    @years_group.command(name="show", description="Show the current year tracking range.")
    async def years_show(self, interaction: discord.Interaction) -> None:
        settings     = await queries.get_settings(self.bot.pool, interaction.guild_id)
        current_year = datetime.now().year
        years_ahead  = settings["years_ahead"]
        year_range   = f"{current_year}–{current_year + years_ahead - 1}" if years_ahead > 1 else str(current_year)
        await interaction.response.send_message(
            f"Currently tracking **{years_ahead} year(s)** of picks ({year_range}).",
            ephemeral=True, delete_after=REPLY_DELETE_AFTER,
        )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Settings(bot))

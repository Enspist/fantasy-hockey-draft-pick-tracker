import discord
from discord import app_commands
from discord.ext import commands

from database import queries
from cogs.checks import has_admin_role
from cogs.picks import post_pick_board


class Teams(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    team = app_commands.Group(name="team", description="Manage fantasy hockey teams.")

    @team.command(name="add", description="Add a new team to the league.")
    @app_commands.describe(name="Team name to add.")
    @has_admin_role()
    async def team_add(self, interaction: discord.Interaction, name: str) -> None:
        try:
            await queries.add_team(self.bot.pool, interaction.guild_id, name)
        except Exception:
            await interaction.response.send_message(
                f"A team named **{name}** already exists.", ephemeral=True
            )
            return

        await interaction.response.send_message(f"Team **{name}** added.", ephemeral=True)
        await post_pick_board(self.bot, interaction.guild_id)

    @team.command(name="rename", description="Rename an existing team.")
    @app_commands.describe(old_name="Current team name.", new_name="New team name.")
    @has_admin_role()
    async def team_rename(self, interaction: discord.Interaction, old_name: str, new_name: str) -> None:
        updated = await queries.rename_team(self.bot.pool, interaction.guild_id, old_name, new_name)
        if not updated:
            await interaction.response.send_message(
                f"No team named **{old_name}** was found.", ephemeral=True
            )
            return

        await interaction.response.send_message(
            f"Team renamed from **{old_name}** to **{new_name}**.", ephemeral=True
        )
        await post_pick_board(self.bot, interaction.guild_id)

    @team.command(name="remove", description="Remove a team from the league.")
    @app_commands.describe(name="Team name to remove.")
    @has_admin_role()
    async def team_remove(self, interaction: discord.Interaction, name: str) -> None:
        deleted = await queries.delete_team(self.bot.pool, interaction.guild_id, name)
        if not deleted:
            await interaction.response.send_message(
                f"No team named **{name}** was found.", ephemeral=True
            )
            return

        await interaction.response.send_message(f"Team **{name}** removed.", ephemeral=True)
        await post_pick_board(self.bot, interaction.guild_id)

    @team.command(name="list", description="List all teams in the league.")
    async def team_list(self, interaction: discord.Interaction) -> None:
        teams = await queries.list_teams(self.bot.pool, interaction.guild_id)
        if not teams:
            await interaction.response.send_message("No teams registered yet.", ephemeral=True)
            return

        names = "\n".join(f"• {t['name']}" for t in teams)
        await interaction.response.send_message(f"**Teams:**\n{names}", ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Teams(bot))

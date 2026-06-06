import discord
from discord import app_commands
from discord.ext import commands

from config import REPLY_DELETE_AFTER
from cogs.checks import has_admin_role


class Management(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    mgmt = app_commands.Group(name="bot", description="Bot management commands.")

    @mgmt.command(name="restart", description="Restart the bot without closing the terminal.")
    @has_admin_role()
    async def mgmt_restart(self, interaction: discord.Interaction) -> None:
        await interaction.response.send_message(
            "Restarting bot…", ephemeral=True, delete_after=REPLY_DELETE_AFTER
        )
        self.bot.request_restart()


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Management(bot))

import discord
from discord import app_commands
from discord.ext import commands

from cogs.checks import has_admin_role


class Management(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    bot_group = app_commands.Group(name="bot", description="Bot management commands.")

    @bot_group.command(name="restart", description="Restart the bot without closing the terminal.")
    @has_admin_role()
    async def bot_restart(self, interaction: discord.Interaction) -> None:
        await interaction.response.send_message("Restarting bot…", ephemeral=True)
        self.bot.request_restart()


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Management(bot))

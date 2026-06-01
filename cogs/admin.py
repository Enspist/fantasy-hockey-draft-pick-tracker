import discord
from discord import app_commands
from discord.ext import commands

from database import queries


class Admin(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="setup", description="Set the channel where pick standings are displayed.")
    @app_commands.describe(channel="The channel to post the draft pick board in.")
    @app_commands.default_permissions(administrator=True)
    async def setup(self, interaction: discord.Interaction, channel: discord.TextChannel) -> None:
        await queries.set_channel(self.bot.pool, interaction.guild_id, channel.id)
        await interaction.response.send_message(
            f"Draft pick board will be posted in {channel.mention}.", ephemeral=True
        )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Admin(bot))

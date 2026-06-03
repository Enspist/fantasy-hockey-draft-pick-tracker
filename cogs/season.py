import discord
from discord import app_commands
from discord.ext import commands

from database import queries
from cogs.checks import has_admin_role
from cogs.picks import _round_label


class Season(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(
        name="season_prep",
        description="Post a checklist of pick movements to make in the fantasy app before the season.",
    )
    @app_commands.describe(year="The upcoming draft year to generate the checklist for.")
    @has_admin_role()
    async def season_prep(self, interaction: discord.Interaction, year: int) -> None:
        guild_id = interaction.guild_id
        traded = await queries.get_traded_picks(self.bot.pool, guild_id)
        season_picks = [p for p in traded if p["season_year"] == year]

        embed = discord.Embed(
            title=f"Season {year} — Draft Pick Movement Checklist",
            description=(
                "Before the draft, make the following pick transfers inside your fantasy hockey app "
                "so ownership is accurately reflected."
            ),
            color=discord.Color.orange(),
        )

        if not season_picks:
            embed.add_field(
                name="No movements needed",
                value=f"All {year} draft picks are still held by their original teams.",
                inline=False,
            )
        else:
            lines = []
            for p in sorted(season_picks, key=lambda x: x["round"]):
                round_label = _round_label(p["round"])
                lines.append(
                    f"• Move **{p['original_team']}**'s {year} {round_label} pick → **{p['current_team']}**"
                )
            embed.add_field(name="Required transfers", value="\n".join(lines), inline=False)

        embed.set_footer(text="Check off each transfer as you complete it.")

        channel_id = await queries.get_channel(self.bot.pool, guild_id)
        if channel_id:
            channel = self.bot.get_channel(channel_id)
            if isinstance(channel, discord.TextChannel):
                await channel.send(embed=embed)
                await interaction.response.send_message(
                    f"Season prep checklist posted to {channel.mention}.", ephemeral=True
                )
                return

        await interaction.response.send_message(embed=embed)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Season(bot))

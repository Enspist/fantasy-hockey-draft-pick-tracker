import asyncio
import logging

import discord
from discord.ext import commands

import config
from database.connection import create_pool

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger(__name__)

COGS = [
    "cogs.admin",
    "cogs.teams",
    "cogs.picks",
    "cogs.season",
]


class FantasyHockeyBot(commands.Bot):
    def __init__(self) -> None:
        intents = discord.Intents.default()
        super().__init__(command_prefix="!", intents=intents)
        self.pool = None

    async def setup_hook(self) -> None:
        self.pool = await create_pool()
        log.info("Database pool created.")

        for cog in COGS:
            await self.load_extension(cog)
            log.info("Loaded cog: %s", cog)

        await self.tree.sync()
        log.info("Slash commands synced.")

    async def on_ready(self) -> None:
        log.info("Logged in as %s (ID: %s)", self.user, self.user.id)

    async def close(self) -> None:
        if self.pool:
            await self.pool.close()
        await super().close()


async def main() -> None:
    bot = FantasyHockeyBot()
    async with bot:
        await bot.start(config.DISCORD_TOKEN)


if __name__ == "__main__":
    asyncio.run(main())

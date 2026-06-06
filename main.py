import asyncio
import logging
import subprocess
from pathlib import Path

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
    "cogs.settings",
    "cogs.teams",
    "cogs.picks",
    "cogs.season",
]

REPO_DIR = Path(__file__).parent.resolve()


def pull_latest() -> None:
    """
    Pull the latest code from main before the bot starts.
    The server only has read (pull) access — pushing is not possible.
    """
    log.info("Pulling latest changes from origin/main…")
    try:
        result = subprocess.run(
            ["git", "-C", str(REPO_DIR), "pull", "origin", "main"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        output = (result.stdout + result.stderr).strip()
        if result.returncode == 0:
            log.info("git pull: %s", output)
        else:
            log.warning("git pull exited with code %d: %s", result.returncode, output)
    except Exception as exc:
        log.warning("git pull failed: %s", exc)


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

        # Sync to the specific guild so commands appear instantly.
        # Global sync can take up to an hour to propagate.
        guild = discord.Object(id=config.GUILD_ID)
        self.tree.copy_global_to(guild=guild)
        await self.tree.sync(guild=guild)
        log.info("Slash commands synced to guild %s.", config.GUILD_ID)

    async def on_ready(self) -> None:
        log.info("Logged in as %s (ID: %s)", self.user, self.user.id)

    async def close(self) -> None:
        if self.pool:
            await self.pool.close()
        await super().close()


async def main() -> None:
    pull_latest()
    bot = FantasyHockeyBot()
    async with bot:
        await bot.start(config.DISCORD_TOKEN)


if __name__ == "__main__":
    asyncio.run(main())

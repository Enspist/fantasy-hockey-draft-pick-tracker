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
    "cogs.management",
    "cogs.settings",
    "cogs.teams",
    "cogs.picks",
    "cogs.season",
]

REPO_DIR = Path(__file__).parent.resolve()


def pull_latest() -> None:
    """Pull the latest code from main before the bot starts."""
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
        self._restart_requested = False

    def request_restart(self) -> None:
        """Signal the main loop to restart the bot after it closes."""
        self._restart_requested = True
        asyncio.create_task(self.close())

    async def setup_hook(self) -> None:
        self.pool = await create_pool()
        log.info("Database pool created.")

        for cog in COGS:
            await self.load_extension(cog)
            log.info("Loaded cog: %s", cog)

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


async def _run_bot() -> bool:
    """
    Start the bot and run until it stops.
    Returns True if a restart was requested, False for a clean shutdown.
    """
    bot = FantasyHockeyBot()
    async with bot:
        await bot.start(config.DISCORD_TOKEN)
    return bot._restart_requested


async def main() -> None:
    pull_latest()
    while True:
        log.info("Starting bot…")
        restart = await _run_bot()
        if restart:
            log.info("Restart requested — restarting bot in 3 seconds…")
            await asyncio.sleep(3)
        else:
            log.info("Bot shut down cleanly.")
            break


if __name__ == "__main__":
    asyncio.run(main())

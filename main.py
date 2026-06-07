import asyncio
import logging
import subprocess
from datetime import datetime
from pathlib import Path

import discord
from discord.ext import commands

import config
from database.connection import create_pool

REPO_DIR = Path(__file__).parent.resolve()
LOGS_DIR = REPO_DIR / "logs"

log = logging.getLogger(__name__)

COGS = [
    "cogs.admin",
    "cogs.management",
    "cogs.settings",
    "cogs.teams",
    "cogs.picks",
    "cogs.season",
]


# ── Logging setup ─────────────────────────────────────────────────────────────

def setup_logging() -> None:
    """
    Configure logging to both the console and a timestamped file in ./logs/.
    Keeps only the newest config.LOG_KEEP log files, deleting older ones.
    A new file is created on every bot start / restart.
    """
    LOGS_DIR.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    log_file  = LOGS_DIR / f"bot_{timestamp}.log"

    fmt     = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    c_handler = logging.StreamHandler()
    c_handler.setFormatter(fmt)
    f_handler = logging.FileHandler(log_file, encoding="utf-8")
    f_handler.setFormatter(fmt)

    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.handlers.clear()
    root.addHandler(c_handler)
    root.addHandler(f_handler)

    # Prune old log files — keep the newest LOG_KEEP, delete the rest
    log_files = sorted(LOGS_DIR.glob("bot_*.log"), key=lambda f: f.stat().st_mtime)
    while len(log_files) > config.LOG_KEEP:
        oldest = log_files.pop(0)
        oldest.unlink()
        logging.getLogger(__name__).debug("Pruned old log: %s", oldest.name)

    log.info("Logging to %s  (keeping last %d log files)", log_file.name, config.LOG_KEEP)


# ── Git pull ──────────────────────────────────────────────────────────────────

def pull_latest() -> None:
    """
    Pull the latest code from the tracking remote branch before starting.
    Uses 'git pull' (no explicit branch) so it follows whatever branch is
    currently checked out — main on production, development during local testing.
    The server only has read access; pushing is not possible.

    Set the environment variable NO_PULL=1 to skip the pull entirely,
    which is useful when testing local changes that haven't been pushed yet.
    """
    import os
    if os.environ.get("NO_PULL"):
        log.info("NO_PULL is set — skipping git pull.")
        return

    log.info("Pulling latest changes from remote…")
    try:
        result = subprocess.run(
            ["git", "-C", str(REPO_DIR), "pull"],
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


# ── Bot ───────────────────────────────────────────────────────────────────────

class FantasyHockeyBot(commands.Bot):
    def __init__(self) -> None:
        intents = discord.Intents.default()
        super().__init__(command_prefix="!", intents=intents)
        self.pool = None
        self._restart_requested = False

    def request_restart(self) -> None:
        """Signal the main loop to restart after the bot closes."""
        self._restart_requested = True
        asyncio.create_task(self.close())

    async def setup_hook(self) -> None:
        self.pool = await create_pool()
        log.info("Database pool created.")

        for cog in COGS:
            await self.load_extension(cog)
            log.info("Loaded cog: %s", cog)

        guild = discord.Object(id=config.GUILD_ID)

        # Cogs register their commands globally on the tree. We copy them to
        # the guild (which preserves autocomplete callbacks) so they appear
        # instantly, then wipe the GLOBAL command set on Discord's side.
        #
        # Why: an earlier version synced commands globally. Those global
        # commands persist on Discord and show up as DUPLICATES alongside the
        # guild copies. Pushing an empty global sync removes them. The guild
        # commands (with autocomplete) are kept.
        self.tree.copy_global_to(guild=guild)

        # 1. Remove leftover global commands from Discord (clears duplicates)
        self.tree.clear_commands(guild=None)
        await self.tree.sync(guild=None)

        # 2. Sync the full command set (with autocomplete) to the guild
        await self.tree.sync(guild=guild)
        log.info("Slash commands synced to guild %s.", config.GUILD_ID)

    async def on_ready(self) -> None:
        log.info("Logged in as %s (ID: %s)", self.user, self.user.id)

    async def close(self) -> None:
        if self.pool:
            await self.pool.close()
        await super().close()


# ── Entry point ───────────────────────────────────────────────────────────────

async def _run_bot() -> bool:
    """Start the bot; return True if a restart was requested."""
    bot = FantasyHockeyBot()
    async with bot:
        await bot.start(config.DISCORD_TOKEN)
    return bot._restart_requested


async def main() -> None:
    setup_logging()
    pull_latest()
    while True:
        log.info("Starting bot…")
        restart = await _run_bot()
        if restart:
            log.info("Restart requested — restarting in 3 seconds…")
            setup_logging()          # fresh log file for the new session
            await asyncio.sleep(3)
        else:
            log.info("Bot shut down cleanly.")
            break


if __name__ == "__main__":
    asyncio.run(main())

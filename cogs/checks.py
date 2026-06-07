"""
Shared permission checks used across cogs.

has_admin_role()     passes if the member holds config.ADMIN_ROLE.
has_bot_admin_role() passes if the member holds config.ADMIN_ROLE OR the
                     optional config.BOT_ADMIN_ROLE (used only by /bot restart).

Server administrators always pass either check, so the bot owner can
always recover access.

Each configured role value can be either:
  - A role name  e.g.  "Commissioner"
  - A role ID    e.g.  "123456789012345678"
"""

import discord
from discord import app_commands

import config


def _member_has_role(member: discord.Member, role_value: str) -> bool:
    """Return True if the member holds the given role (by name or ID)."""
    target = role_value.strip()
    if not target:
        return False
    for role in member.roles:
        if str(role.id) == target or role.name.lower() == target.lower():
            return True
    return False


def has_admin_role() -> app_commands.checks:
    """Slash-command check: member must have the configured admin role."""

    async def predicate(interaction: discord.Interaction) -> bool:
        member = interaction.user
        if isinstance(member, discord.Member) and member.guild_permissions.administrator:
            return True
        if isinstance(member, discord.Member) and _member_has_role(member, config.ADMIN_ROLE):
            return True
        raise app_commands.CheckFailure(
            f"You need the **{config.ADMIN_ROLE}** role to use this command."
        )

    return app_commands.check(predicate)


def has_bot_admin_role() -> app_commands.checks:
    """
    Slash-command check for bot-management commands (e.g. /bot restart).

    Passes for server administrators, the main admin role, or the optional
    BOT_ADMIN_ROLE.  If BOT_ADMIN_ROLE is not configured it is simply
    ignored, so this behaves like has_admin_role() in that case.
    """

    async def predicate(interaction: discord.Interaction) -> bool:
        member = interaction.user
        if isinstance(member, discord.Member):
            if member.guild_permissions.administrator:
                return True
            if _member_has_role(member, config.ADMIN_ROLE):
                return True
            if config.BOT_ADMIN_ROLE and _member_has_role(member, config.BOT_ADMIN_ROLE):
                return True

        needed = f"**{config.ADMIN_ROLE}**"
        if config.BOT_ADMIN_ROLE:
            needed += f" or **{config.BOT_ADMIN_ROLE}**"
        raise app_commands.CheckFailure(f"You need the {needed} role to use this command.")

    return app_commands.check(predicate)

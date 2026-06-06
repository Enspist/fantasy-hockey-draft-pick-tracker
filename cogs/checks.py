"""
Shared permission checks used across cogs.

has_admin_role() passes if the invoking member holds the role whose name
or ID matches config.ADMIN_ROLE.  Server administrators always pass
regardless of role, so the bot owner can always recover access.

config.ADMIN_ROLE can be either:
  - A role name  e.g.  "Commissioner"
  - A role ID    e.g.  "123456789012345678"
"""

import discord
from discord import app_commands

import config


def _member_has_admin_role(member: discord.Member) -> bool:
    """Return True if the member holds the configured admin role."""
    admin = config.ADMIN_ROLE.strip()
    for role in member.roles:
        # Match by ID (numeric string) or by name (case-insensitive)
        if str(role.id) == admin or role.name.lower() == admin.lower():
            return True
    return False


def has_admin_role() -> app_commands.checks:
    """Slash-command check: member must have the configured admin role."""

    async def predicate(interaction: discord.Interaction) -> bool:
        member = interaction.user
        # Server administrators always pass
        if isinstance(member, discord.Member) and member.guild_permissions.administrator:
            return True
        if isinstance(member, discord.Member) and _member_has_admin_role(member):
            return True
        raise app_commands.CheckFailure(
            f"You need the **{config.ADMIN_ROLE}** role to use this command."
        )

    return app_commands.check(predicate)

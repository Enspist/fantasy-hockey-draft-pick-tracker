"""
Shared permission checks used across cogs.

has_admin_role() passes if the invoking member holds the role whose name
matches config.ADMIN_ROLE (case-insensitive).  Server administrators always
pass regardless of role, so the bot owner can always recover access.
"""

import discord
from discord import app_commands

import config


def has_admin_role() -> app_commands.checks:
    """Slash-command check: member must have the configured admin role."""

    async def predicate(interaction: discord.Interaction) -> bool:
        member = interaction.user
        # Server admins bypass the role requirement
        if isinstance(member, discord.Member) and member.guild_permissions.administrator:
            return True
        if isinstance(member, discord.Member):
            role_names = {r.name.lower() for r in member.roles}
            if config.ADMIN_ROLE.lower() in role_names:
                return True
        raise app_commands.CheckFailure(
            f"You need the **{config.ADMIN_ROLE}** role to use this command."
        )

    return app_commands.check(predicate)

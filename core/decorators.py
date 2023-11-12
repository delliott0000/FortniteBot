from __future__ import annotations
from typing import TYPE_CHECKING

from discord import app_commands

if TYPE_CHECKING:
    from resources.extras import FortniteInteraction


def is_not_blacklisted():

    async def predicate(interaction: FortniteInteraction) -> bool:
        uid = interaction.user.id

        _blacklisted = await interaction.client.database_client.is_blacklisted(uid)
        if _blacklisted is True:
            raise app_commands.CheckFailure('You have been blacklisted from using this feature.')

        return True

    return app_commands.check(predicate)


def is_not_logged_in():

    async def predicate(interaction: FortniteInteraction) -> bool:
        uid = interaction.user.id

        _logged_in = bool(interaction.client.get_auth_session(uid))
        if _logged_in is True:
            raise app_commands.CheckFailure('You must be logged out to use this feature.')
        return True

    return app_commands.check(predicate)


def is_logged_in():

    async def predicate(interaction: FortniteInteraction) -> bool:
        uid = interaction.user.id

        _logged_in = bool(interaction.client.get_auth_session(uid))
        if _logged_in is False:
            raise app_commands.CheckFailure('You must be logged in to use this feature.')
        return True

    return app_commands.check(predicate)


def is_premium():

    async def predicate(interaction: FortniteInteraction) -> bool:
        uid = interaction.user.id

        _premium = await interaction.client.database_client.is_premium(uid)
        if _premium is False:
            raise app_commands.CheckFailure('You must be a premium user to use this feature.')

        return True

    return app_commands.check(predicate)


def is_owner():

    async def predicate(interaction: FortniteInteraction) -> bool:
        uid = interaction.user.id

        _is_owner = uid in interaction.client.owner_ids
        if _is_owner is False:
            raise app_commands.CheckFailure('That command is owner-only.')

        return True

    return app_commands.check(predicate)


def non_premium_cooldown():

    async def predicate(interaction: FortniteInteraction) -> app_commands.Cooldown | None:
        uid = interaction.user.id

        _premium = await interaction.client.database_client.is_premium(uid)
        if _premium is False:
            return app_commands.Cooldown(1, 15)

    return app_commands.checks.dynamic_cooldown(predicate)

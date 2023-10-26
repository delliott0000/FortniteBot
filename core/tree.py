from __future__ import annotations
from typing import TYPE_CHECKING

from datetime import timedelta

if TYPE_CHECKING:
    from core.decorators import FortniteInteraction

from discord import app_commands


class CustomTree(app_commands.CommandTree):

    async def on_error(self, interaction: FortniteInteraction, error: app_commands.AppCommandError) -> None:
        if isinstance(error, app_commands.CommandOnCooldown):
            td = timedelta(seconds=round(error.retry_after))
            message = f'You\'re on cooldown. Try again in `{td}`.'

        elif isinstance(error, app_commands.CommandInvokeError):
            message = str(error.original)

        else:
            message = str(error)

        await interaction.client.bad_response(interaction, message)

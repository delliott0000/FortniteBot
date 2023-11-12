from __future__ import annotations
from typing import TYPE_CHECKING

from core.group import CustomGroup
from core.decorators import is_owner

from discord import app_commands, User
from discord.utils import format_dt

if TYPE_CHECKING:
    from core.bot import FortniteBot
    from resources.extras import FortniteInteraction


# noinspection PyUnresolvedReferences
class UtilityCommands(CustomGroup):

    @is_owner()
    @app_commands.describe(
        user='The Discord user to add premium to.',
        duration='The duration of premium (e.g. 1w for one week).')
    @app_commands.command(description='Add premium to a user for the specified duration.')
    async def premium(self, interaction: FortniteInteraction, user: User, duration: str) -> None:
        await interaction.response.defer(thinking=True, ephemeral=True)

        td = interaction.client.string_to_duration(duration)
        until = await interaction.client.database_client.add_premium(user.id, td)

        message = f'**Added `{td}` of premium to {interaction.user.mention} (expires {format_dt(until)}).**'
        await interaction.client.send_response(interaction, message)

    @is_owner()
    @app_commands.describe(user='The Discord user whose premium is being removed.')
    @app_commands.command(description='Remove premium status from a user.')
    async def unpremium(self, interaction: FortniteInteraction, user: User) -> None:
        await interaction.response.defer(thinking=True, ephemeral=True)

        await interaction.client.database_client.expire_premium(user.id)

        message = f'**Removed premium status from {interaction.user.mention}.**'
        await interaction.client.send_response(interaction, message)

    @is_owner()
    @app_commands.describe(user='The Discord user being (un)blacklisted.')
    @app_commands.command(description='Toggle the blacklist status of a user.')
    async def blacklist(self, interaction: FortniteInteraction, user: User) -> None:
        await interaction.response.defer(thinking=True, ephemeral=True)

        result = await interaction.client.database_client.toggle_blacklist(user.id)

        message = f'**Set blacklist status for {interaction.user.mention} to `{result}`.**'
        await interaction.client.send_response(interaction, message)


async def setup(bot: FortniteBot) -> None:
    bot.tree.add_command(UtilityCommands(name='utility'))

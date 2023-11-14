from __future__ import annotations
from typing import TYPE_CHECKING

from datetime import datetime, timedelta

from core.group import CustomGroup
from core.decorators import is_owner, is_not_blacklisted, non_premium_cooldown
from components.embed import CustomEmbed

import psutil
from discord import app_commands, User
from discord.utils import format_dt

if TYPE_CHECKING:
    from core.bot import FortniteBot
    from resources.extras import FortniteInteraction


# noinspection PyUnresolvedReferences
class UtilityCommands(CustomGroup):

    @non_premium_cooldown()
    @is_not_blacklisted()
    @app_commands.command(description='View some of the bot\'s system information.')
    async def info(self, interaction: FortniteInteraction) -> None:
        await interaction.response.defer(thinking=True, ephemeral=True)

        process = psutil.Process()

        converter = 1 / 1024 ** 2
        unit = 'MB'

        total_memory = round(psutil.virtual_memory().total * converter, 2)

        mem = process.memory_info()
        mem_mb = round(mem.rss * converter, 2)
        mem_prcnt = round(100 * mem_mb / total_memory, 2)
        cpu_prcnt = round(100 * process.cpu_percent(), 2)

        since = datetime.fromtimestamp(process.create_time())
        uptime = interaction.client.now - since
        uptime -= timedelta(microseconds=uptime.microseconds)

        embed = CustomEmbed(
            colour=interaction.client.colour(interaction.guild))
        embed.set_author(name='Process Info', icon_url=interaction.client.user.avatar)

        embed.add_field(
            name='Owners',
            value=f'> {" ".join(owner.mention for owner in interaction.client.owners)}',
            inline=False)
        embed.add_field(
            name='Memory',
            value=f'> **Usage (%): `{mem_prcnt:,}`**\n'
                  f'> **Usage ({unit}): `{mem_mb:,}`**\n'
                  f'> **System Total ({unit}): `{total_memory:,}`**')
        embed.add_field(
            name='CPU',
            value=f'> **Usage (%): `{cpu_prcnt:,}`**')
        embed.add_field(
            name='Uptime',
            value=f'> **Online For: `{uptime}`**\n'
                  f'> **Since: {format_dt(since)}**',
            inline=False)
        embed.add_field(
            name='Ping',
            value=f'> **Websocket Latency (MS): `{round(interaction.client.latency, 3):,}`**')

        await interaction.followup.send(embed=embed)

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

from __future__ import annotations
from typing import TYPE_CHECKING

from core.decorators import is_not_blacklisted
from components.embed import CustomEmbed
from components.paginator import Paginator
from resources.emojis import emojis

from discord import app_commands

if TYPE_CHECKING:
    from core.bot import FortniteBot
    from resources.extras import FortniteInteraction


# noinspection PyUnresolvedReferences
class HelpCommands(app_commands.Group):

    __opt_map__: dict[bool, str] = {True: '', False: 'opt'}

    @is_not_blacklisted()
    @app_commands.command(description='View information about the bot\'s commands.')
    async def menu(self, interaction: FortniteInteraction) -> None:
        await interaction.response.defer(thinking=True, ephemeral=True)

        embeds: list[CustomEmbed] = []

        for group_got in interaction.client.tree.get_commands():
            if isinstance(group_got, app_commands.Group):
                group_synced = next(group for group in interaction.client.app_commands if group.name == group_got.name)

                embed = CustomEmbed(
                    title=f'{group_got.name.capitalize()} Commands',
                    description=f'{emojis["clock"]} **- 15s Cooldown (Non-Premium)**\n'
                                f'{emojis["premium"]} **- Premium Command**',
                    colour=interaction.client.colour(interaction.guild))
                embed.set_author(name='Help Menu', icon_url=interaction.client.user.avatar)

                for command_got in group_got.commands:
                    prem: str = emojis['premium'] if [c for c in command_got.checks if 'is_premium' in str(c)] else ''
                    cool: str = emojis['clock'] if [c for c in command_got.checks if '_cooldown_' in str(c)] else ''

                    command_synced = next(cmd for cmd in group_synced.options if cmd.name == command_got.name)
                    opts = [f'{self.__opt_map__[opt.required]}<{opt.name}>' for opt in command_synced.options]

                    embed.add_field(
                        name=f'{prem} {cool} {command_synced.mention}',
                        value=f'> **Description:** `{command_got.description}`\n'
                              f'> **Parameters:** `{" ".join(opts) if opts else "`None`"}`',
                        inline=False)

                embeds.append(embed)

        for embed in embeds:
            embed.set_footer(text=f'Page {embeds.index(embed) + 1} of {len(embeds)}')

        view = Paginator(interaction, embeds)
        await interaction.followup.send(embed=embeds[0], view=view)


async def setup(bot: FortniteBot) -> None:
    bot.tree.add_command(HelpCommands(name='help'))

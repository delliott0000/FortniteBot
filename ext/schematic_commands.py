from __future__ import annotations
from typing import TYPE_CHECKING

from core.decorators import is_not_blacklisted, is_logged_in, non_premium_cooldown, account_kwargs
from core.errors import FortniteException
from components.itemselect import RecycleSelect, UpgradeSelect
from components.paginator import Paginator
from components.embed import EmbedField
from resources.emojis import emojis
from fortnite.stw import Schematic

if TYPE_CHECKING:
    from core.bot import FortniteBot
    from core.auth import AuthSession
    from core.decorators import FortniteInteraction
    from components.embed import CustomEmbed
    from fortnite.base import Account
    from discord import Colour

from discord import app_commands, User


# noinspection PyUnresolvedReferences
class SchematicCommands(app_commands.Group):

    @staticmethod
    def _schematics_to_embeds(
        interaction: FortniteInteraction,
        schematics: list[Schematic],
        **kwargs: str | int | Colour
    ) -> list[CustomEmbed]:
        embed_fields = []

        for schematic in schematics:

            perks = f'> {emojis["perk"]} **Perks:** ' \
                    f'{"".join([emojis["perk_rarities"][perk.rarity] for perk in schematic.perks])}\n' if \
                schematic.perks else ''

            embed_field = EmbedField(
                name=f'{schematic.emoji} {schematic.name}',
                value=f'> {emojis["level"]} **Level:** `{schematic.level}`\n'
                      f'> {emojis["tiers"][schematic.tier][schematic.material]} **Tier:** `{schematic.tier}`\n'
                      f'> {emojis["power"]} **PL:** `{schematic.power_level}`\n'
                      f'{perks}'
                      f'> {emojis["id"]} **Item ID:** `{schematic.item_id}`\n'
                      f'> {emojis["favourite"]} **Favorite:** '
                      f'{emojis["check" if schematic.favourite is True else "cross"]}',
                inline=False)

            embed_fields.append(embed_field)

        return interaction.client.fields_to_embeds(embed_fields, **kwargs)

    @staticmethod
    async def _fetch_schematics(auth_session: AuthSession, account: Account, name: str) -> list[Schematic]:
        schematics = await account.schematics(auth_session)
        schematics = [schematic for schematic in schematics if name.lower() in schematic.name.lower()]

        if not schematics:
            raise FortniteException(f'Schematic `{name}` not found.')

        return schematics

    @non_premium_cooldown()
    @is_logged_in()
    @is_not_blacklisted()
    @app_commands.describe(name='The name of the schematic.', **account_kwargs)
    @app_commands.command(description='View your own or another player\'s schematics.')
    async def list(
        self,
        interaction: FortniteInteraction,
        name: str = '',
        display: str | None = None,
        epic_id: str | None = None,
        user: User | None = None
    ) -> None:
        await interaction.response.defer(thinking=True, ephemeral=True)

        auth_session = interaction.client.get_auth_session(interaction.user.id)
        if display or epic_id or user:
            account = await interaction.client.account_from_kwargs(
                auth_session,
                display=display,
                epic_id=epic_id,
                user=user)
        else:
            account = await auth_session.account()

        icon_url = await account.icon_url(auth_session)
        schematics = await self._fetch_schematics(auth_session, account, name)

        embeds = self._schematics_to_embeds(
            interaction,
            schematics,
            description=f'**IGN:** `{account.display}`',
            colour=interaction.client.colour(interaction.guild),
            author_name='Schematic List',
            author_icon=icon_url)
        view = Paginator(interaction, embeds)

        await interaction.followup.send(embed=embeds[0], view=view)

    @non_premium_cooldown()
    @is_logged_in()
    @is_not_blacklisted()
    @app_commands.choices(material=[
        app_commands.Choice(name='Ore', value='Ore'),
        app_commands.Choice(name='Crystal', value='Crystal')])
    @app_commands.command(description='Upgrade one of your schematics.')
    async def upgrade(
        self,
        interaction: FortniteInteraction,
        name: str = '',
        new_level: int = 50,
        material: app_commands.Choice[str] | None = None
    ) -> None:
        await interaction.response.defer(thinking=True, ephemeral=True)

        auth_session = interaction.client.get_auth_session(interaction.user.id)
        account = await auth_session.account()

        icon_url = await account.icon_url(auth_session)
        schematics = await self._fetch_schematics(auth_session, account, name)

        embeds = self._schematics_to_embeds(
            interaction,
            schematics,
            description=interaction.user.mention,
            colour=interaction.client.colour(interaction.guild),
            author_name='Upgrade Schematics',
            author_icon=icon_url,
        )
        view = Paginator(interaction, embeds)
        view.add_item(UpgradeSelect(schematics, new_level, material.value if material else None))

        await interaction.followup.send(embed=embeds[0], view=view)

    @non_premium_cooldown()
    @is_logged_in()
    @is_not_blacklisted()
    @app_commands.describe(name='The name of the schematic.')
    @app_commands.command(description='Recycle one of your schematics.')
    async def recycle(self, interaction: FortniteInteraction, name: str = '') -> None:
        await interaction.response.defer(thinking=True, ephemeral=True)

        auth_session = interaction.client.get_auth_session(interaction.user.id)
        account = await auth_session.account()

        icon_url = await account.icon_url(auth_session)
        schematics = await self._fetch_schematics(auth_session, account, name)

        embeds = self._schematics_to_embeds(
            interaction,
            schematics,
            description=interaction.user.mention,
            colour=interaction.client.colour(interaction.guild),
            author_name='Recycle Schematics',
            author_icon=icon_url)
        view = Paginator(interaction, embeds)
        view.add_item(RecycleSelect(schematics))

        await interaction.followup.send(embed=embeds[0], view=view)


async def setup(bot: FortniteBot) -> None:
    bot.tree.add_command(SchematicCommands(name='schematic'))

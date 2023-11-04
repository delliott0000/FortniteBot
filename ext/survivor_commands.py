from __future__ import annotations
from typing import TYPE_CHECKING

from typing import get_args
from core.decorators import is_not_blacklisted, is_logged_in, non_premium_cooldown
from core.errors import FortniteException
from components.itemselect import RecycleSelect, UpgradeSelect
from components.paginator import Paginator
from components.embed import EmbedField
from resources.emojis import emojis
from resources.extras import Personality, account_kwargs
from fortnite.stw import Survivor

if TYPE_CHECKING:
    from core.bot import FortniteBot
    from core.auth import AuthSession
    from components.embed import CustomEmbed
    from resources.extras import FortniteInteraction, GenericSurvivor, Account
    from discord import Colour

from discord import app_commands, User


# noinspection PyUnresolvedReferences
class SurvivorCommands(app_commands.Group):

    Personalities = [app_commands.Choice(name=choice, value=choice) for choice in get_args(Personality)]

    @staticmethod
    def _survivors_to_embeds(
        interaction: FortniteInteraction,
        survivors: list[GenericSurvivor],
        **kwargs: str | int | Colour
    ) -> list[CustomEmbed]:
        embed_fields = []

        for survivor in survivors:

            extras = emojis['set_bonuses'][survivor.set_bonus_type] if isinstance(survivor, Survivor) else \
                emojis['lead_survivors'][survivor.preferred_squad_name]

            embed_field = EmbedField(
                name=f'{survivor.emoji} {emojis["personalities"][survivor.personality]} {extras} {survivor.name}',
                value=f'> {emojis["level"]} **Level:** `{survivor.level}`\n'
                      f'> {emojis["tiers"][survivor.tier][None]} **Tier:** `{survivor.tier}`\n'
                      f'> {emojis["power"]} **PL:** `{survivor.base_power_level}`\n'
                      f'> {emojis["id"]} **Item ID:** `{survivor.item_id}`\n'
                      f'> {emojis["favourite"]} **Favorite:** '
                      f'{emojis["check" if survivor.favourite is True else "cross"]}',
                inline=False)

            embed_fields.append(embed_field)

        return interaction.client.fields_to_embeds(embed_fields, **kwargs)

    @staticmethod
    async def _fetch_survivors(
        auth_session: AuthSession,
        account: Account,
        name: str,
        personality: app_commands.Choice[str] | None
    ) -> list[GenericSurvivor]:
        survivors = await account.survivors(auth_session)
        survivors = [survivor for survivor in survivors if name.lower() in survivor.name.lower() and
                     (not personality or personality.name == survivor.personality)]

        if not survivors:
            raise FortniteException(f'Survivor `{name}` not found.')

        return survivors

    @non_premium_cooldown()
    @is_logged_in()
    @is_not_blacklisted()
    @app_commands.choices(personality=Personalities)
    @app_commands.describe(
        name='The name of the survivor.',
        personality='The personality of the survivor.',
        **account_kwargs)
    @app_commands.command(description='View your own or another player\'s survivors.')
    async def list(
        self,
        interaction: FortniteInteraction,
        name: str = '',
        personality: app_commands.Choice[str] | None = None,
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
        survivors = await self._fetch_survivors(auth_session, account, name, personality)

        embeds = self._survivors_to_embeds(
            interaction,
            survivors,
            description=f'**IGN:** `{account.display}`',
            colour=interaction.client.colour(interaction.guild),
            author_name='Survivor List',
            author_icon=icon_url)
        view = Paginator(interaction, embeds)

        await interaction.followup.send(embed=embeds[0], view=view)

    @non_premium_cooldown()
    @is_logged_in()
    @is_not_blacklisted()
    @app_commands.choices(personality=Personalities)
    @app_commands.describe(
        name='The name of the survivor.',
        personality='The personality of the survivor.',
        level='The desired level of the survivor.')
    @app_commands.command(description='Upgrade one of your survivors.')
    async def upgrade(
        self,
        interaction: FortniteInteraction,
        name: str = '',
        personality: app_commands.Choice[str] | None = None,
        level: int = 50
    ) -> None:
        await interaction.response.defer(thinking=True, ephemeral=True)

        auth_session = interaction.client.get_auth_session(interaction.user.id)
        account = await auth_session.account()

        icon_url = await account.icon_url(auth_session)
        survivors = await self._fetch_survivors(auth_session, account, name, personality)

        embeds = self._survivors_to_embeds(
            interaction,
            survivors,
            description=interaction.user.mention,
            colour=interaction.client.colour(interaction.guild),
            author_name='Upgrade Survivors',
            author_icon=icon_url,
        )
        view = Paginator(interaction, embeds)
        view.add_item(UpgradeSelect(survivors, level, None))

        await interaction.followup.send(embed=embeds[0], view=view)

    @non_premium_cooldown()
    @is_logged_in()
    @is_not_blacklisted()
    @app_commands.choices(personality=Personalities)
    @app_commands.describe(
        name='The name of the survivor.',
        personality='The personality of the survivor.')
    @app_commands.command(description='Recycle one of your survivors.')
    async def recycle(
        self,
        interaction: FortniteInteraction,
        name: str = '',
        personality: app_commands.Choice[str] | None = None,
    ) -> None:
        await interaction.response.defer(thinking=True, ephemeral=True)

        auth_session = interaction.client.get_auth_session(interaction.user.id)
        account = await auth_session.account()

        icon_url = await account.icon_url(auth_session)
        survivors = await self._fetch_survivors(auth_session, account, name, personality)

        embeds = self._survivors_to_embeds(
            interaction,
            survivors,
            description=interaction.user.mention,
            colour=interaction.client.colour(interaction.guild),
            author_name='Recycle Survivors',
            author_icon=icon_url)
        view = Paginator(interaction, embeds)
        view.add_item(RecycleSelect(survivors))

        await interaction.followup.send(embed=embeds[0], view=view)


async def setup(bot: FortniteBot) -> None:
    bot.tree.add_command(SurvivorCommands(name='survivor'))

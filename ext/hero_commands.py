from __future__ import annotations
from typing import TYPE_CHECKING

from typing import get_args

from core.group import CustomGroup
from core.decorators import is_not_blacklisted, is_logged_in, non_premium_cooldown
from components.itemselect import RecycleSelect, UpgradeSelect
from components.paginator import Paginator
from resources.extras import HeroType, account_kwargs

from discord import app_commands, User

if TYPE_CHECKING:
    from core.bot import FortniteBot
    from resources.extras import FortniteInteraction


# noinspection PyUnresolvedReferences
class HeroCommands(CustomGroup):

    Categories = [app_commands.Choice(name=choice, value=choice) for choice in get_args(HeroType)]

    @non_premium_cooldown()
    @is_logged_in()
    @is_not_blacklisted()
    @app_commands.choices(category=Categories)
    @app_commands.describe(
        name='The name of the hero.',
        category='Search by type of hero (e.g. Constructor).',
        **account_kwargs)
    @app_commands.command(description='View your own or another player\'s heroes.')
    async def list(
        self,
        interaction: FortniteInteraction,
        name: str = '',
        category: app_commands.Choice[str] | None = None,
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
        heroes = await self.fetch_heroes(auth_session, account, name, category)

        fields = self.heroes_to_fields(heroes, show_ids=False)
        embeds = interaction.client.fields_to_embeds(
            fields,
            field_limit=4,
            colour=interaction.client.colour(interaction.guild),
            description=f'**IGN:** `{account.display}`',
            author_name='Hero List',
            author_icon=icon_url)
        view = Paginator(interaction, embeds)

        await interaction.followup.send(embed=embeds[0], view=view)

    @non_premium_cooldown()
    @is_logged_in()
    @is_not_blacklisted()
    @app_commands.choices(category=Categories)
    @app_commands.describe(
        name='The name of the hero.',
        category='Search by type of hero (e.g. Constructor).',
        level='The desired level of the hero.')
    @app_commands.command(description='Upgrade one of your heroes.')
    async def upgrade(
        self,
        interaction: FortniteInteraction,
        name: str = '',
        category: app_commands.Choice[str] | None = None,
        level: int = 50
    ) -> None:
        await interaction.response.defer(thinking=True, ephemeral=True)

        auth_session = interaction.client.get_auth_session(interaction.user.id)
        account = await auth_session.account()

        icon_url = await account.icon_url(auth_session)
        heroes = await self.fetch_heroes(auth_session, account, name, category)

        fields = self.heroes_to_fields(heroes)
        embeds = interaction.client.fields_to_embeds(
            fields,
            colour=interaction.client.colour(interaction.guild),
            description=interaction.user.mention,
            author_name='Upgrade Heroes',
            author_icon=icon_url)
        view = Paginator(interaction, embeds)
        view.add_item(UpgradeSelect(heroes, level, None))

        await interaction.followup.send(embed=embeds[0], view=view)

    @non_premium_cooldown()
    @is_logged_in()
    @is_not_blacklisted()
    @app_commands.choices(category=Categories)
    @app_commands.describe(
        name='The name of the hero.',
        category='Search by type of hero (e.g. Constructor).')
    @app_commands.command(description='Recycle one of your heroes.')
    async def recycle(
        self,
        interaction: FortniteInteraction,
        name: str = '',
        category: app_commands.Choice[str] | None = None
    ) -> None:
        await interaction.response.defer(thinking=True, ephemeral=True)

        auth_session = interaction.client.get_auth_session(interaction.user.id)
        account = await auth_session.account()

        icon_url = await account.icon_url(auth_session)
        heroes = await self.fetch_heroes(auth_session, account, name, category)

        fields = self.heroes_to_fields(heroes)
        embeds = interaction.client.fields_to_embeds(
            fields,
            colour=interaction.client.colour(interaction.guild),
            description=interaction.user.mention,
            author_name='Recycle Heroes',
            author_icon=icon_url)
        view = Paginator(interaction, embeds)
        view.add_item(RecycleSelect(heroes))

        await interaction.followup.send(embed=embeds[0], view=view)


async def setup(bot: FortniteBot) -> None:
    bot.tree.add_command(HeroCommands(name='hero'))

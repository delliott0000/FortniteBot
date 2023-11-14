from __future__ import annotations
from typing import TYPE_CHECKING

from typing import get_args

from core.group import CustomGroup
from core.decorators import is_not_blacklisted, is_logged_in, non_premium_cooldown
from components.itemselect import RecycleSelect, UpgradeSelect
from components.paginator import Paginator
from resources.extras import Personality, account_kwargs

from discord import app_commands, User

if TYPE_CHECKING:
    from core.bot import FortniteBot
    from resources.extras import FortniteInteraction


# noinspection PyUnresolvedReferences
class SurvivorCommands(CustomGroup):

    Personalities = [app_commands.Choice(name=choice, value=choice) for choice in get_args(Personality)]

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
        survivors = await self.fetch_survivors(auth_session, account, name, personality)

        fields = self.survivors_to_fields(survivors, show_ids=False)
        embeds = interaction.client.fields_to_embeds(
            fields,
            colour=interaction.client.colour(interaction.guild),
            description=f'**IGN:** `{account.display}`',
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
        survivors = await self.fetch_survivors(auth_session, account, name, personality)

        fields = self.survivors_to_fields(survivors)
        embeds = interaction.client.fields_to_embeds(
            fields,
            colour=interaction.client.colour(interaction.guild),
            description=interaction.user.mention,
            author_name='Upgrade Survivors',
            author_icon=icon_url)
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
        survivors = await self.fetch_survivors(auth_session, account, name, personality)

        fields = self.survivors_to_fields(survivors)
        embeds = interaction.client.fields_to_embeds(
            fields,
            colour=interaction.client.colour(interaction.guild),
            description=interaction.user.mention,
            author_name='Recycle Survivors',
            author_icon=icon_url)
        view = Paginator(interaction, embeds)
        view.add_item(RecycleSelect(survivors))

        await interaction.followup.send(embed=embeds[0], view=view)


async def setup(bot: FortniteBot) -> None:
    bot.tree.add_command(SurvivorCommands(name='survivor'))

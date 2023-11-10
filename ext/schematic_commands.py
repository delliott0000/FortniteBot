from __future__ import annotations
from typing import TYPE_CHECKING

from core.group import CustomGroup
from core.decorators import is_not_blacklisted, is_logged_in, non_premium_cooldown
from components.itemselect import RecycleSelect, UpgradeSelect
from components.paginator import Paginator
from resources.extras import account_kwargs

from discord import app_commands, User

if TYPE_CHECKING:
    from core.bot import FortniteBot
    from resources.extras import FortniteInteraction


# noinspection PyUnresolvedReferences
class SchematicCommands(CustomGroup):

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
        schematics = await self.fetch_schematics(auth_session, account, name)

        fields = self.schematics_to_fields(schematics, show_ids=False)
        embeds = interaction.client.fields_to_embeds(
            fields,
            colour=interaction.client.colour(interaction.guild),
            description=f'**IGN:** `{account.display}`',
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
    @app_commands.describe(
        name='The name of the schematic.',
        level='The desired level of the schematic.',
        material='The desired upgrade path of the schematic, if applicable.')
    @app_commands.command(description='Upgrade one of your schematics.')
    async def upgrade(
        self,
        interaction: FortniteInteraction,
        name: str = '',
        level: int = 50,
        material: app_commands.Choice[str] | None = None
    ) -> None:
        await interaction.response.defer(thinking=True, ephemeral=True)

        auth_session = interaction.client.get_auth_session(interaction.user.id)
        account = await auth_session.account()

        icon_url = await account.icon_url(auth_session)
        schematics = await self.fetch_schematics(auth_session, account, name)

        fields = self.schematics_to_fields(schematics)
        embeds = interaction.client.fields_to_embeds(
            fields,
            colour=interaction.client.colour(interaction.guild),
            description=interaction.user.mention,
            author_name='Upgrade Schematics',
            author_icon=icon_url)
        view = Paginator(interaction, embeds)
        view.add_item(UpgradeSelect(schematics, level, material.value if material else None))

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
        schematics = await self.fetch_schematics(auth_session, account, name)

        fields = self.schematics_to_fields(schematics)
        embeds = interaction.client.fields_to_embeds(
            fields,
            colour=interaction.client.colour(interaction.guild),
            description=interaction.user.mention,
            author_name='Recycle Schematics',
            author_icon=icon_url)
        view = Paginator(interaction, embeds)
        view.add_item(RecycleSelect(schematics))

        await interaction.followup.send(embed=embeds[0], view=view)


async def setup(bot: FortniteBot) -> None:
    bot.tree.add_command(SchematicCommands(name='schematic'))

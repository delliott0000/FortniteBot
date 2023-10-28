from __future__ import annotations
from typing import TYPE_CHECKING

from core.decorators import is_not_blacklisted, is_logged_in, non_premium_cooldown
from components.paginator import Paginator
from components.embed import EmbedField
from resources.emojis import emojis

if TYPE_CHECKING:
    from core.bot import FortniteBot
    from core.decorators import FortniteInteraction
    from core.account import _FriendTypes

from discord import app_commands


# noinspection PyUnresolvedReferences
class FriendsCommands(app_commands.Group):

    __auth_mapping__: dict[str, str] = {
        'friends': 'Friends List',
        'incoming': 'Incoming Requests',
        'outgoing': 'Outgoing Requests',
        'suggested': 'Suggested Friends',
        'blocklist': 'Blocked Users'
    }

    async def send_friends(self, interaction: FortniteInteraction, friend_type: _FriendTypes) -> None:
        await interaction.response.defer(thinking=True, ephemeral=True)

        auth_session = interaction.client.get_auth_session(interaction.user.id)
        account = await auth_session.account()
        icon_url = await account.icon_url(auth_session)
        friends = await account.friends_list(friend_type=friend_type)

        field_list: list[EmbedField] = []

        for friend in friends:
            discord_id = interaction.client.discord_id_from_account_id(friend.id)
            linked_str = f'{emojis["check"]} <@{discord_id}>' if discord_id is not None else f'{emojis["cross"]}'

            field = EmbedField(
                name=friend.display,
                value=f'> **Epic ID:** `{friend.id}`\n'
                      f'> **Logged in with {interaction.client.user.name}:** {linked_str}',
                inline=False)

            field_list.append(field)

        embeds = interaction.client.fields_to_embeds(
            field_list,
            description=interaction.user.mention,
            colour=interaction.client.colour(interaction.guild),
            author_name=self.__auth_mapping__[friend_type],
            author_icon=icon_url)
        view = Paginator(interaction, embeds)
        await interaction.followup.send(embed=embeds[0], view=view)

    @non_premium_cooldown()
    @is_logged_in()
    @is_not_blacklisted()
    @app_commands.command(description='View your Epic Games friends list.')
    async def list(self, interaction: FortniteInteraction) -> None:
        await self.send_friends(interaction, 'friends')

    @non_premium_cooldown()
    @is_logged_in()
    @is_not_blacklisted()
    @app_commands.command(description='View your Epic Games friends list.')
    async def incoming(self, interaction: FortniteInteraction) -> None:
        await self.send_friends(interaction, 'incoming')

    @non_premium_cooldown()
    @is_logged_in()
    @is_not_blacklisted()
    @app_commands.command(description='View your Epic Games friends list.')
    async def outgoing(self, interaction: FortniteInteraction) -> None:
        await self.send_friends(interaction, 'outgoing')

    @non_premium_cooldown()
    @is_logged_in()
    @is_not_blacklisted()
    @app_commands.command(description='View your Epic Games friends list.')
    async def suggested(self, interaction: FortniteInteraction) -> None:
        await self.send_friends(interaction, 'suggested')

    @non_premium_cooldown()
    @is_logged_in()
    @is_not_blacklisted()
    @app_commands.command(description='View your Epic Games friends list.')
    async def blocklist(self, interaction: FortniteInteraction) -> None:
        await self.send_friends(interaction, 'blocklist')


async def setup(bot: FortniteBot):
    bot.tree.add_command(FriendsCommands(name='friends'))

from __future__ import annotations
from typing import TYPE_CHECKING

from typing import Literal, Callable, Awaitable
from core.decorators import is_not_blacklisted, is_logged_in, non_premium_cooldown
from components.paginator import Paginator
from components.embed import EmbedField
from resources.emojis import emojis

if TYPE_CHECKING:
    from core.bot import FortniteBot
    from core.decorators import FortniteInteraction
    from core.account import _FriendTypes, PartialEpicAccount
    from core.https import _Dict

from discord.utils import format_dt
from discord import app_commands, User


# noinspection PyUnresolvedReferences
class FriendsCommands(app_commands.Group):

    __auth_mapping__: dict[str, str] = {
        'friends': 'Friends List',
        'incoming': 'Incoming Requests',
        'outgoing': 'Outgoing Requests',
        'suggested': 'Suggested Friends',
        'blocklist': 'Blocked Users'
    }

    async def _show_friends(self, interaction: FortniteInteraction, friend_type: _FriendTypes) -> None:
        await interaction.response.defer(thinking=True, ephemeral=True)

        auth_session = interaction.client.get_auth_session(interaction.user.id)
        account = await auth_session.account()
        icon_url = await account.icon_url(auth_session)
        friends = await account.friends_list(friend_type=friend_type)

        field_list: list[EmbedField] = []

        for friend in friends:
            account = friend['account']
            discord_id = interaction.client.discord_id_from_account_id(account.id)
            linked_str = f'{emojis["check"]} <@{discord_id}>' if discord_id is not None else f'{emojis["cross"]}'
            since = friend["created"]

            field = EmbedField(
                name=account.display,
                value=f'> **Epic ID:** `{account.id}`\n'
                      f'> **Favourite:** {emojis["check" if friend["favorite"] is True else "cross"]}\n'
                      f'> **Mutual:** `{friend["mutual"]}`\n'
                      f'> **Alias:** `{friend["alias"]}`\n'
                      f'> **Note:** `{friend["note"]}`\n'
                      f'> **Since: {format_dt(since) if since is not None else "`None`"}**\n'
                      f'> **Logged in with {interaction.client.user.name}:** {linked_str}',
                inline=False)

            field_list.append(field)

        embeds = interaction.client.fields_to_embeds(
            field_list,
            field_limit=4,
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
        await self._show_friends(interaction, 'friends')

    @non_premium_cooldown()
    @is_logged_in()
    @is_not_blacklisted()
    @app_commands.command(description='View your incoming friend requests.')
    async def incoming(self, interaction: FortniteInteraction) -> None:
        await self._show_friends(interaction, 'incoming')

    @non_premium_cooldown()
    @is_logged_in()
    @is_not_blacklisted()
    @app_commands.command(description='View your outgoing friend requests.')
    async def outgoing(self, interaction: FortniteInteraction) -> None:
        await self._show_friends(interaction, 'outgoing')

    @non_premium_cooldown()
    @is_logged_in()
    @is_not_blacklisted()
    @app_commands.command(description='View your suggested friends list.')
    async def suggested(self, interaction: FortniteInteraction) -> None:
        await self._show_friends(interaction, 'suggested')

    @non_premium_cooldown()
    @is_logged_in()
    @is_not_blacklisted()
    @app_commands.command(description='View your list of blocked users.')
    async def blocklist(self, interaction: FortniteInteraction) -> None:
        await self._show_friends(interaction, 'blocklist')

    @staticmethod
    async def _friend_operation(
        interaction: FortniteInteraction,
        operation_str: Literal['friend', 'unfriend', 'block', 'unblock'],
        display: str | None,
        epic_id: str | None,
        user: User | None
    ) -> None:
        await interaction.response.defer(thinking=True, ephemeral=True)

        host_auth_session = interaction.client.get_auth_session(interaction.user.id)
        host_account = await host_auth_session.account()

        if user is not None:
            account = await interaction.client.account_from_discord_id(user.id)
        else:
            account = await host_auth_session.fetch_account(display=display, account_id=epic_id)

        operation: Callable[[PartialEpicAccount], Awaitable[_Dict]] = getattr(host_account, operation_str)
        await operation(account)

        await interaction.client.send_response(interaction, f'Successfully {operation_str}ed `{account.display}`.')

    @non_premium_cooldown()
    @is_logged_in()
    @is_not_blacklisted()
    @app_commands.describe(
        display='Search by Epic display name.',
        epic_id='Search by Epic account ID.',
        user='Search by Discord user.')
    @app_commands.command(description='Send a friend request or accept an incoming one.')
    async def add(
        self,
        interaction: FortniteInteraction,
        display: str | None = None,
        epic_id: str | None = None,
        user: User | None = None
    ) -> None:
        await self._friend_operation(interaction, 'friend', display=display, epic_id=epic_id, user=user)

    @non_premium_cooldown()
    @is_logged_in()
    @is_not_blacklisted()
    @app_commands.describe(
        display='Search by Epic display name.',
        epic_id='Search by Epic account ID.',
        user='Search by Discord user.')
    @app_commands.command(description='Unfriend a user or decline an incoming request.')
    async def remove(
        self,
        interaction: FortniteInteraction,
        display: str | None = None,
        epic_id: str | None = None,
        user: User | None = None
    ) -> None:
        await self._friend_operation(interaction, 'unfriend', display=display, epic_id=epic_id, user=user)

    @non_premium_cooldown()
    @is_logged_in()
    @is_not_blacklisted()
    @app_commands.describe(
        display='Search by Epic display name.',
        epic_id='Search by Epic account ID.',
        user='Search by Discord user.')
    @app_commands.command(description='Block an Epic Games account.')
    async def block(
        self,
        interaction: FortniteInteraction,
        display: str | None = None,
        epic_id: str | None = None,
        user: User | None = None
    ) -> None:
        await self._friend_operation(interaction, 'block', display=display, epic_id=epic_id, user=user)

    @non_premium_cooldown()
    @is_logged_in()
    @is_not_blacklisted()
    @app_commands.describe(
        display='Search by Epic display name.',
        epic_id='Search by Epic account ID.',
        user='Search by Discord user.')
    @app_commands.command(description='Unblock an Epic Games account.')
    async def unblock(
        self,
        interaction: FortniteInteraction,
        display: str | None = None,
        epic_id: str | None = None,
        user: User | None = None
    ) -> None:
        await self._friend_operation(interaction, 'unblock', display=display, epic_id=epic_id, user=user)


async def setup(bot: FortniteBot) -> None:
    bot.tree.add_command(FriendsCommands(name='friends'))

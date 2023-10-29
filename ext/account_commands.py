from __future__ import annotations
from typing import TYPE_CHECKING

from core.decorators import is_not_blacklisted, is_not_logged_in, is_logged_in, non_premium_cooldown
from components.embed import CustomEmbed
from components.login import LoginView
from resources.emojis import emojis

if TYPE_CHECKING:
    from core.bot import FortniteBot
    from core.decorators import FortniteInteraction

from discord import app_commands, User
from discord.utils import format_dt


# noinspection PyUnresolvedReferences
class AccountCommands(app_commands.Group):

    @non_premium_cooldown()
    @is_not_logged_in()
    @is_not_blacklisted()
    @app_commands.command(description='Log into your Epic Games account.')
    async def login(self, interaction: FortniteInteraction) -> None:
        await interaction.response.defer(thinking=True, ephemeral=True)

        embed = CustomEmbed(
            title='__How To Log In__',
            description=f'**• Step 1:** Log into Epic Games on your browser and open '
                        f'[this link]({interaction.client.http_client.USER_AUTH_URL}) '
                        f'(or click the "Get Code" button below).\n\n'
                        f'**• Step 2:** Copy the 32-digit code labelled "authorizationCode".\n\n'
                        f'**• Step 3:** Click the button labelled "Submit Code". '
                        f'This will bring up a form where you can paste your authorization code. '
                        f'Paste the code in and click "Submit".\n\n'
                        f'**• Step 4:** You\'re done!\n\n'
                        f'**This message will time out after 2 minutes.**\n\n'
                        f':warning: To switch accounts with **{interaction.client.user.name}**, '
                        f'you must log out of your current account before logging back in on your new account.',
            colour=interaction.client.colour(interaction.guild))
        embed.set_author(name='Register Epic Account', icon_url=interaction.client.user.avatar)
        view = LoginView(interaction)

        await interaction.followup.send(embed=embed, view=view)

    @non_premium_cooldown()
    @is_logged_in()
    # Blacklisted users can still log out
    @app_commands.command(description='Log out of your Epic Games account.')
    async def logout(self, interaction: FortniteInteraction) -> None:
        await interaction.response.defer(thinking=True, ephemeral=True)

        auth_session = interaction.client.get_auth_session(interaction.user.id)
        interaction.client.remove_auth_session(interaction.user.id)

        await auth_session.kill()
        await interaction.client.send_response(interaction, 'Successfully logged out.')

    @non_premium_cooldown()
    @is_logged_in()
    @is_not_blacklisted()
    @app_commands.command(description='View your Epic Games account information.')
    async def info(self, interaction: FortniteInteraction) -> None:
        await interaction.response.defer(thinking=True, ephemeral=True)

        auth_session = interaction.client.get_auth_session(interaction.user.id)
        account = await auth_session.account()
        icon_url = await account.icon_url(auth_session)

        embed = CustomEmbed(
            description=interaction.user.mention,
            colour=interaction.client.colour(interaction.guild))
        embed.set_author(name='Epic Account Info', icon_url=icon_url)
        embed.set_footer(text='Do not share any sensitive information with anyone!')

        _n = '`None`'
        display_last_updated = _n if account.display_last_updated is None else format_dt(account.display_last_updated)
        date_of_birth = _n if account.date_of_birth is None else format_dt(account.date_of_birth)
        last_login = _n if account.last_login is None else format_dt(account.last_login)

        embed.add_field(
            name='Personal Details:',
            value=f'> **Name:** `{account.real_name}`\n'
                  f'> **Country:** `{account.country}`\n'
                  f'> **Language:** `{account.language}`\n'
                  f'> **Date of Birth: {date_of_birth}**\n',
            inline=False)
        embed.add_field(
            name='Display Name:',
            value=f'> **Current:** `{account.display}`\n'
                  f'> **Changes:** `{account.display_changes}`\n'
                  f'> **Last Changed: {display_last_updated}**\n'
                  f'> **Changeable:** {emojis["check" if account.can_update_display is True else "cross"]}',
            inline=False)
        embed.add_field(
            name='Email:',
            value=f'> **Current:** `{account.email}`\n'
                  f'> **Verified:** '
                  f'{emojis["check" if account.verified is True else "cross"]}',
            inline=False)
        embed.add_field(
            name='Login Details:',
            value=f'> **Last Login: {last_login}**\n'
                  f'> **Failed Login Attempts:** `{account.failed_logins}`\n'
                  f'> **TFA Enabled:** {emojis["check" if account.tfa_enabled else "cross"]}',
            inline=False)
        embed.add_field(
            name='Login Credentials:',
            value=f'> **Epic ID:** `{account.id}`\n'
                  f'> **Access Token:** `{auth_session.access_token}`\n'
                  f'> **Refresh Token:** `{auth_session.refresh_token}`\n',
            inline=False)

        await interaction.followup.send(embed=embed)

    @non_premium_cooldown()
    @is_logged_in()
    @is_not_blacklisted()
    @app_commands.command(description='Search for an account by ID, display name or Discord user.')
    async def search(
        self,
        interaction: FortniteInteraction,
        display: str | None = None,
        epic_id: str | None = None,
        user: User | None = None
    ) -> None:
        await interaction.response.defer(thinking=True, ephemeral=True)

        auth_session = interaction.client.get_auth_session(interaction.user.id)

        if user is not None:
            account = await interaction.client.account_from_discord_id(user.id)
        else:
            account = await auth_session.fetch_account(display=display, account_id=epic_id)

        icon_url = await account.icon_url(auth_session)
        discord_id = interaction.client.discord_id_from_account_id(account.id)
        linked_str = f'{emojis["check"]} <@{discord_id}>' if discord_id is not None else f'{emojis["cross"]}'

        embed = CustomEmbed(colour=interaction.client.colour(interaction.guild))
        embed.set_author(name='Epic Account Info', icon_url=icon_url)
        embed.add_field(
            name='Found Account:',
            value=f'> **Display Name:** `{account.display}`\n'
                  f'> **Epic ID:** `{account.id}`\n'
                  f'> **Logged in with {interaction.client.user.name}:** {linked_str}',)

        await interaction.followup.send(embed=embed)


async def setup(bot: FortniteBot) -> None:
    bot.tree.add_command(AccountCommands(name='account'))

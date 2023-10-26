from __future__ import annotations
from typing import TYPE_CHECKING

from core.decorators import is_not_blacklisted, is_not_logged_in, is_logged_in, non_premium_cooldown
from components.embed import CustomEmbed
from components.login import LoginView

if TYPE_CHECKING:
    from core.bot import FortniteBot
    from core.decorators import FortniteInteraction

from discord import app_commands


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
            colour=interaction.client.colour(interaction.guild)
        )
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


async def setup(bot: FortniteBot):
    bot.tree.add_command(AccountCommands(name='account'))

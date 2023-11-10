from __future__ import annotations
from typing import TYPE_CHECKING

from core.group import CustomGroup
from core.decorators import is_not_blacklisted, is_logged_in, non_premium_cooldown
from components.paginator import Paginator
from resources.extras import account_kwargs

from discord import app_commands, User

if TYPE_CHECKING:
    from core.bot import FortniteBot
    from resources.extras import FortniteInteraction


# noinspection PyUnresolvedReferences
class SquadCommands(CustomGroup):

    @non_premium_cooldown()
    @is_logged_in()
    @is_not_blacklisted()
    @app_commands.describe(**account_kwargs)
    @app_commands.command(description='View your own or another player\'s survivor squads.')
    async def list(
        self,
        interaction: FortniteInteraction,
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
        squads = await account.squads(auth_session)

        embeds = self.squads_to_embeds(
            squads,
            colour=interaction.client.colour(interaction.guild),
            icon_url=icon_url)
        view = Paginator(interaction, embeds)

        await interaction.followup.send(embed=embeds[0], view=view)


async def setup(bot: FortniteBot) -> None:
    bot.tree.add_command(SquadCommands(name='squad'))

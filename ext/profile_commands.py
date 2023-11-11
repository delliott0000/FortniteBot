from __future__ import annotations
from typing import TYPE_CHECKING

from core.group import CustomGroup
from core.decorators import is_not_blacklisted, is_logged_in, non_premium_cooldown
from components.embed import CustomEmbed
from resources.emojis import emojis
from resources.extras import account_kwargs, resource_categories

from discord import app_commands, User

if TYPE_CHECKING:
    from core.bot import FortniteBot
    from resources.extras import FortniteInteraction


# noinspection PyUnresolvedReferences
class ProfileCommands(CustomGroup):

    @non_premium_cooldown()
    @is_logged_in()
    @is_not_blacklisted()
    @app_commands.describe(**account_kwargs)
    @app_commands.command(description='View your own or another player\'s STW resources.')
    async def resources(
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
        resources = await account.resources(auth_session)

        embed = CustomEmbed(
            colour=interaction.client.colour(interaction.guild),
            description=f'**IGN:** `{account.display}`')
        embed.set_author(name='Profile Resources', icon_url=icon_url)
        embed.set_footer(text='* Weapon/Hero Voucher counts may be incorrect due to API issues.')

        for category, resource_list in resource_categories.items():
            resources_sublist = [resource for resource in resources if resource.name in resource_list]
            value = '\n'.join(f'> {resource.emoji} **{resource.quantity:,}**' for resource in resources_sublist) or '> `None`'
            embed.add_field(name=category, value=value)
        embed.insert_field_at(2, name='\u200b', value='\u200b')

        try:
            # Should deal with seasonal tickets changing every few months
            tickets = next(r for r in resources if ('Ticket' in r.name or r.name == 'Candy') and 'X-Ray' not in r.name)
            prev_field = embed.fields[-2]
            embed.set_field_at(
                -2,
                name=prev_field.name,
                value=prev_field.value + f'\n> {emojis["resources"]["Tickets"]} **{tickets.quantity:,}**')
        except StopIteration:
            pass

        await interaction.followup.send(embed=embed)


async def setup(bot: FortniteBot) -> None:
    bot.tree.add_command(ProfileCommands(name='profile'))

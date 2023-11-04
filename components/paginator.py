from __future__ import annotations
from typing import TYPE_CHECKING

from components.view import CustomView

from discord.ui import button
from discord import Button, ButtonStyle

if TYPE_CHECKING:
    from resources.extras import FortniteInteraction
    from components.embed import CustomEmbed


class Paginator(CustomView):

    def __init__(self, interaction: FortniteInteraction, embeds: list[CustomEmbed], **kwargs: float | None) -> None:
        super().__init__(interaction, **kwargs)
        self.embeds: list[CustomEmbed] = embeds
        self.current_page: int = 1
        self.update_buttons()

    def update_buttons(self) -> None:
        for item in self.children:
            item.disabled = False
        self.firs_page.disabled = self.prev_page.disabled = self.current_page == 1
        self.last_page.disabled = self.next_page.disabled = self.current_page == len(self.embeds)

    async def edit_page(self, interaction: FortniteInteraction) -> None:
        # noinspection PyUnresolvedReferences
        await interaction.response.defer()
        self.update_buttons()
        await interaction.edit_original_response(embed=self.embeds[self.current_page - 1], view=self)

    @button(label='<<')
    async def firs_page(self, interaction: FortniteInteraction, _: Button) -> None:
        self.current_page = 1
        await self.edit_page(interaction)

    @button(label='<', style=ButtonStyle.blurple)
    async def prev_page(self, interaction: FortniteInteraction, _: Button) -> None:
        self.current_page -= 1
        await self.edit_page(interaction)

    @button(label='>', style=ButtonStyle.blurple)
    async def next_page(self, interaction: FortniteInteraction, _: Button) -> None:
        self.current_page += 1
        await self.edit_page(interaction)

    @button(label='>>')
    async def last_page(self, interaction: FortniteInteraction, _: Button) -> None:
        self.current_page = len(self.embeds)
        await self.edit_page(interaction)

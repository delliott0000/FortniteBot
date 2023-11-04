from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from resources.extras import FortniteInteraction

from discord.ui import View, Item
from discord import HTTPException


class CustomView(View):

    def __init__(self, interaction: FortniteInteraction, **kwargs: float | None) -> None:
        super().__init__(**kwargs)
        self.interaction: FortniteInteraction = interaction

    async def on_error(self, interaction: FortniteInteraction, error: Exception, item: Item) -> None:
        message = str(error)

        await interaction.client.bad_response(interaction, message)

    async def on_timeout(self) -> None:
        for item in self.children:
            item.disabled = True
        try:
            await self.interaction.edit_original_response(view=self)
        except HTTPException:
            pass

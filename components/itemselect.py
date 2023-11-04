from __future__ import annotations
from typing import TYPE_CHECKING

from core.errors import FortniteException
from fortnite.stw import Schematic

if TYPE_CHECKING:
    from fortnite.stw import Recyclable, Upgradable
    from resources.extras import FortniteInteraction, Selectable, Material

from discord import ui, SelectOption


class ItemSelect(ui.Select):

    def __init__(self, items: list[Selectable]) -> None:
        if len(items) > 25:
            items = items[:25]

        options = [SelectOption(label=f'Item ID: {item.item_id[:8]}...', value=item.item_id) for item in items]
        super().__init__(placeholder='Select Item...', options=options)
        self.items: list[Selectable] = items

    def get_selected_item(self, interaction: FortniteInteraction) -> Selectable:
        try:
            selected_id = interaction.data['values'][0]
            return next(item for item in self.items if item.item_id == selected_id)
        except (TypeError, KeyError, IndexError, StopIteration):
            raise FortniteException('Something went wrong, please try again.')


class RecycleSelect(ItemSelect):

    async def callback(self, interaction: FortniteInteraction) -> None:
        # noinspection PyUnresolvedReferences
        await interaction.response.defer(thinking=True, ephemeral=True)
        item: Recyclable = self.get_selected_item(interaction)

        await item.recycle()
        await interaction.client.send_response(interaction, f'Successfully recycled `{item.name}`.')


class UpgradeSelect(ItemSelect):

    def __init__(self, items: list[Selectable], new_level: int, new_material: Material | None = None) -> None:
        super().__init__(items)

        self.new_level: int = new_level
        self.new_tier: int = min((new_level - 1) // 10 + 1, 5)
        self.new_material: Material | None = new_material

    async def callback(self, interaction: FortniteInteraction) -> None:
        # noinspection PyUnresolvedReferences
        await interaction.response.defer(thinking=True, ephemeral=True)
        item: Upgradable = self.get_selected_item(interaction)

        conversion_index = item.conversion_index(self.new_material) if isinstance(item, Schematic) else -1

        await item.upgrade(self.new_level, self.new_tier, conversion_index)
        await interaction.client.send_response(interaction, f'`{item.name}` has been upgraded to level `{item.level}`!')

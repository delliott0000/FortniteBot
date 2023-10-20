from __future__ import annotations
from typing import TYPE_CHECKING

from typing import Any

from resources.lookup import lookup
from resources.emojis import emojis
from fortnite.base import BaseEntity
from core.errors import UnknownTemplateID

if TYPE_CHECKING:
    from fortnite.base import MaybeAccount


class SaveTheWorldItem(BaseEntity):

    def __init__(
            self,
            account: MaybeAccount,
            item_id: str,
            template_id: str,
            attributes: dict[str, Any]
    ) -> None:
        super().__init__(account, item_id, template_id)

        for tid_variation in [
            template_id,
            template_id[:-2] + '01',
            template_id.replace('Trap:tid', 'Schematic:sid')[:-2] + '01',
            template_id.replace('Weapon:wid', 'Schematic:sid')[:-2] + '01'
        ]:
            if tid_variation in lookup['Items']:
                lookup_id = tid_variation
                break
        else:
            raise UnknownTemplateID(item_id, template_id)

        self.name: str = lookup['Items'][lookup_id]['name']
        self.rarity: str = lookup['Items'][lookup_id]['rarity']
        self.type: str = lookup['Item Types'][lookup['Items'][lookup_id]['type']]

        self.level: int = attributes.get('level', 1)
        self.favourite: bool = attributes.get('favorite', False)

        self.tier: int = int(template_id[-1]) if template_id[-1].isdigit() else 1

    @property
    def emoji(self) -> str:
        return emojis['resources'].get(self.name) or emojis['rarities'][self.rarity]

from __future__ import annotations
from typing import TYPE_CHECKING

from resources.lookup import lookup
from resources.emojis import emojis
from fortnite.base import AccountBoundMixin, BaseEntity
from core.errors import UnknownTemplateID, MalformedItemAttributes, ItemIsReadOnly

if TYPE_CHECKING:
    from fortnite.base import Account, Attributes


class SaveTheWorldItem(BaseEntity):

    __slots__ = (
        'name',
        'type',
        'tier',
        'level',
        'rarity',
        'favourite'
    )

    def __init__(self, item_id: str, template_id: str, attributes: Attributes) -> None:
        super().__init__(item_id, template_id, attributes)

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
        self.type: str = lookup['Item Types'][lookup['Items'][lookup_id]['type']]
        self.tier: int = int(template_id[-1]) if template_id[-1].isdigit() else 1
        self.level: int = attributes.get('level', 1)
        self.rarity: str = lookup['Items'][lookup_id]['rarity']
        self.favourite: bool = attributes.get('favorite', False)

    @property
    def emoji(self) -> str:
        return emojis['resources'].get(self.name) or emojis['rarities'].get(self.rarity, '')

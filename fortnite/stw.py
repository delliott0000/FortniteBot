from __future__ import annotations
from typing import TYPE_CHECKING

from typing import Literal
from weakref import ref

from resources.lookup import lookup
from resources.emojis import emojis
from fortnite.base import AccountBoundMixin, BaseEntity
from core.errors import UnknownTemplateID, MalformedItemAttributes, ItemIsReadOnly

if TYPE_CHECKING:
    from weakref import ReferenceType
    from fortnite.base import Account, Attributes
    from core.auth import AuthSession


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


class Recyclable(AccountBoundMixin, SaveTheWorldItem):

    __slots__ = (
        '_account',
    )

    @property
    def auth_checker(self) -> AuthSession:
        try:
            return self.account.auth_session
        except AttributeError:
            raise ItemIsReadOnly(self)

    async def recycle(self) -> dict:
        data = await self.auth_checker.profile_operation(
            route='client',
            operation='RecycleItem',
            json={
                'targetItemId':
                    self.item_id
            }
        )

        return data


class Upgradable(Recyclable):

    __tier_mapping__: dict[int, str] = {1: 'i', 2: 'ii', 3: 'iii', 4: 'iv', 5: 'v'}

    async def upgrade(self, new_level: int, new_tier: int, conversion_index: int) -> dict:
        data = await self.auth_checker.profile_operation(
            route='client',
            operation='UpgradeItemBulk',
            json={
                'targetItemId':
                    self.item_id,
                'desiredLevel':
                    new_level,
                'desiredTier':
                    self.__tier_mapping__.get(new_tier, 'v'),
                'conversionRecipeIndexChoice':
                    conversion_index
            }
        )

        self.level = new_level
        self.tier = new_tier

        if isinstance(self, Schematic) and self.tier > 3 and conversion_index == 1:
            self.template_id = self.template_id.replace('_ore_', '_crystal_')

        return data


class Schematic(Upgradable):

    __slots__ = (
        'perks',
    )

    __index_mapping__: dict[str, int] = {'Crystal': 1, 'Ore': 0}

    def __init__(self, account: Account, item_id: str, template_id: str, attributes: Attributes) -> None:
        try:
            super().__init__(account, item_id, template_id, attributes)
        except UnknownTemplateID:
            super().__init__(account, item_id, template_id.replace('_crystal_', '_ore_'), attributes)
            self.template_id = template_id

        self.perks: list[SchematicPerk] = [SchematicPerk(self, pid) for pid in attributes.get('alterations', [])]

    @property
    def power_level(self) -> int:
        return lookup['Item Power Levels']['Other'][self.rarity][str(self.tier)][str(self.level)]

    @property
    def material(self) -> str | None:
        if self.tier == 4 and '_ore_' in self.template_id:
            return 'Obsidian'
        elif self.tier == 4:
            return 'Shadow Shard'
        elif self.tier == 5 and '_ore_' in self.template_id:
            return 'Brightcore'
        elif self.tier == 5:
            return 'Sunbeam'

    def conversion_index(self, target_material: Literal['Crystal', 'Ore'], target_tier: int = 5) -> int:
        if self.tier <= 3 and target_tier > 3:
            return self.__index_mapping__.get(target_material, 1)
        return -1


class SchematicPerk:

    __slots__ = (
        '_schematic',
        'id',
        'rarity',
        'description'
    )

    def __init__(self, schematic: Schematic, perk_id: str) -> None:
        self._schematic: ReferenceType[Schematic] = ref(schematic)
        self.id: str = perk_id

        try:
            self.rarity: str = ['common', 'uncommon', 'rare', 'epic', 'legendary'][int(perk_id[-1]) - 1]
        except (ValueError, IndexError):
            self.rarity: str = 'common'

        self.description: str | None = None

    @property
    def schematic(self) -> Schematic:
        return self._schematic()


class SurvivorBase(Upgradable):

    __slots__ = (
        'personality',
        'squad_index',
        'squad_id',
        'squad_name'
    )

    def __init__(self, account: Account, item_id: str, template_id: str, attributes: Attributes) -> None:
        super().__init__(account, item_id, template_id, attributes)

        try:
            self.personality: str = attributes['personality'].split('.')[-1][2:]
            self.squad_index: int = attributes['squad_slot_idx']
        except KeyError:
            raise MalformedItemAttributes(item_id, template_id, attributes)

        self.squad_id: str | None = attributes.get('squad_id')
        self.squad_name: str | None = lookup['Survivor Squads'].get(self.squad_id)


class Survivor(SurvivorBase):

    __slots__ = (
        'set_bonus_type',
        'set_bonus_data'
    )

    def __init__(self, account: Account, item_id: str, template_id: str, attributes: Attributes) -> None:
        super().__init__(account, item_id, template_id, attributes)

        try:
            self.set_bonus_type: str = attributes['set_bonus'].split('.')[-1][2:].replace('Low', '').replace('High', '')
            self.set_bonus_data: dict[str, str | int | None] = lookup['Set Bonuses'][self.set_bonus_type]
        except KeyError:
            raise MalformedItemAttributes(item_id, template_id, attributes)

    @property
    def base_power_level(self) -> int:
        return lookup['Item Power Levels']['Survivor'][self.rarity][str(self.tier)][str(self.level)]


class LeadSurvivor(SurvivorBase):

    __slots__ = (
        'preferred_squad_name',
    )

    def __init__(self, account: Account, item_id: str, template_id: str, attributes: Attributes) -> None:
        super().__init__(account, item_id, template_id, attributes)

        try:
            self.preferred_squad_name: str = lookup['Leads Preferred Squad'][attributes['managerSynergy']]
        except KeyError:
            raise MalformedItemAttributes(item_id, template_id, attributes)

    @property
    def base_power_level(self) -> int:
        return lookup['Item Power Levels']['Lead Survivor'][self.rarity][str(self.tier)][str(self.level)]

from __future__ import annotations
from typing import TYPE_CHECKING

from typing import Literal, TypedDict, get_args
from weakref import ref

from resources.lookup import lookup
from resources.emojis import emojis
from fortnite.base import AccountBoundMixin, BaseEntity
from core.errors import UnknownTemplateID, MalformedItemAttributes, ItemIsReadOnly, ItemIsFavourited

if TYPE_CHECKING:
    from weakref import ReferenceType
    from fortnite.base import Account, Attributes
    from core.auth import AuthSession


_FortType = Literal[
    'Fortitude',
    'Offense',
    'Resistance',
    'Tech']

_SetBonusType = Literal[
    'TrapDurability',
    'RangedDamage',
    'MeleeDamage',
    'TrapDamage',
    'AbilityDamage',
    'Fortitude',
    'Resistance',
    'ShieldRegen']

_HeroType = Literal[
    'Commando',
    'Constructor',
    'Outlander',
    'Ninja']


class _FortStats(TypedDict):

    Fortitude: int
    Offense: int
    Resistance: int
    Tech: int


class SaveTheWorldItem(BaseEntity):

    __slots__ = (
        'name',
        'type',
        'tier',
        'level',
        'rarity',
        'favourite'
    )

    def __init__(self, template_id: str, attributes: Attributes) -> None:
        super().__init__(template_id, attributes)

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
            raise UnknownTemplateID(self)

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
        'item_id'
    )

    @property
    def auth_checker(self) -> AuthSession:
        try:
            return self.account.auth_session
        except AttributeError:
            raise ItemIsReadOnly(self)

    async def recycle(self) -> dict:
        if self.favourite is True:
            raise ItemIsFavourited(self)

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

    __slots__ = ()

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
            raise MalformedItemAttributes(self)

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
            self.set_bonus_type: _SetBonusType = \
                attributes['set_bonus'].split('.')[-1][2:].replace('Low', '').replace('High', '')
            self.set_bonus_data: dict[str, str | int | None] = lookup['Set Bonuses'][self.set_bonus_type]
        except KeyError:
            raise MalformedItemAttributes(self)

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
            raise MalformedItemAttributes(self)

    @property
    def base_power_level(self) -> int:
        return lookup['Item Power Levels']['Lead Survivor'][self.rarity][str(self.tier)][str(self.level)]


class ActiveSetBonus:

    __slots__ = (
        'squad',
        'name',
        'points',
        'fort_type',
        'fort_stats'
    )

    def __init__(self, squad: SurvivorSquad, name: _SetBonusType, points: int, fort_type: _FortType | None) -> None:
        self.squad: SurvivorSquad = squad
        self.name: _SetBonusType = name
        self.points: int = points
        self.fort_type: _FortType | None = fort_type

        self.fort_stats: _FortStats = dict(Fortitude=0, Offense=0, Resistance=0, Tech=0)
        if self.fort_type is not None:
            self.fort_stats[self.fort_type] += points


class SurvivorSquad(AccountBoundMixin):

    __slots__ = (
        '_account',
        'item_id',
        'name',
        'lead_survivor',
        'survivors'
    )

    def __init__(
        self,
        account: Account,
        squad_id: str,
        lead_survivor: LeadSurvivor | None = None,
        survivors: list[Survivor] | None = None
    ) -> None:
        super().__init__(account, squad_id)

        self.name: str = lookup['Survivor Squads'][squad_id]
        self.lead_survivor: LeadSurvivor | None = lead_survivor
        self.survivors: list[Survivor] = survivors.copy() if survivors is not None else []
        self.survivors.sort(key=lambda survivor: survivor.squad_index)

    @property
    def active_set_bonuses(self) -> list[ActiveSetBonus]:
        tally: dict[_SetBonusType, int] = {_bonus_type: 0 for _bonus_type in get_args(_SetBonusType)}

        for survivor in self.survivors:
            tally[survivor.set_bonus_type] += 1

        active_set_bonuses = []

        for bonus_type, count in tally.items():
            name: _SetBonusType = lookup['Set Bonuses'][bonus_type]['name']
            points: int = lookup['Set Bonuses'][bonus_type]['bonus']
            fort_type: _FortType = lookup['Set Bonuses'][bonus_type]['bonus_type']

            for _ in range(count // lookup['Set Bonuses'][bonus_type]['requirement']):
                active_set_bonus = ActiveSetBonus(self, name, points, fort_type)
                active_set_bonuses.append(active_set_bonus)

        return active_set_bonuses

    @property
    def fort_stats(self) -> _FortStats:
        fort_stats: _FortStats = dict(Fortitude=0, Offense=0, Resistance=0, Tech=0)

        for active_set_bonus in self.active_set_bonuses:
            for fort_type, points in active_set_bonus.fort_stats.items():
                fort_type: _FortType
                fort_stats[fort_type] += points

        survivor_point_count: int = 0

        if self.lead_survivor is not None:
            if self.lead_survivor.preferred_squad_name == self.name:
                survivor_point_count += self.lead_survivor.base_power_level * 2
            else:
                survivor_point_count += self.lead_survivor.base_power_level

        for survivor in self.survivors:
            pl = survivor.base_power_level
            leader_bonus_increments: dict[str, tuple[int, int]] = lookup['Lead Bonus Increment']

            if self.lead_survivor is not None and self.lead_survivor.personality == survivor.personality:
                pl += leader_bonus_increments[self.lead_survivor.rarity][0]
            elif self.lead_survivor is not None:
                pl += leader_bonus_increments[self.lead_survivor.rarity][1]

            survivor_point_count += pl

        name_to_fort_type: _FortType = lookup['Survivor Squads FORT'][self.name]
        fort_stats[name_to_fort_type] += survivor_point_count

        return fort_stats


class MissionAlertReward(SaveTheWorldItem):

    __slots__ = (
        'quantity',
    )

    def __init__(self, template_id: str, quantity: int) -> None:
        super().__init__(template_id, {})
        self.quantity: int = quantity


class AccountResource(AccountBoundMixin, MissionAlertReward):

    __slots__ = (
        '_account',
        'item_id'
    )


class MissionAlert:

    __slots__ = (
        'name',
        'theme',
        'power',
        'theater',
        'four_player',
        'alert_rewards'
    )

    def __init__(
        self,
        name: str,
        theme: str,
        theater: str,
        power_data: str,
        alert_rewards: list[MissionAlertReward] | None = None
    ) -> None:
        self.name: str = name
        self.theme: str = theme
        self.theater: str = theater
        self.alert_rewards: list[MissionAlertReward] = alert_rewards or []

        split_power_data: list[str] = power_data.split(' ')
        self.four_player: bool = 'Players' in split_power_data
        try:
            self.power: int = int(split_power_data[0])
        except ValueError:
            self.power: int = 0


class Hero(Upgradable):

    __slots__ = (
        'type',
        'support_perk_name',
        'support_perk_desc',
        'commander_perk_name',
        'commander_perk_desc'
    )

    def __init__(self, account: Account, item_id: str, template_id: str, attributes: Attributes) -> None:
        super().__init__(account, item_id, template_id, attributes)

        self.type: _HeroType | None = next((ht for ht in get_args(_HeroType) if ht.lower() in self.template_id), None)

        perk_data: dict[str, str] = lookup['Hero Perks'].get(self.name, {})
        self.support_perk_name: str | None = perk_data.get('support_perk_name')
        self.support_perk_desc: str | None = perk_data.get('support_perk_desc')
        self.commander_perk_name: str | None = None if self.support_perk_name is None else self.support_perk_name + ' +'
        self.commander_perk_desc: str | None = perk_data.get('commander_perk_desc')

    @property
    def power_level(self) -> int:
        return lookup['Item Power Levels']['Other'][self.rarity][str(self.tier)][str(self.level)]

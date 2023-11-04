from typing import TYPE_CHECKING, Literal, Any

if TYPE_CHECKING:

    from typing import TypeVar

    from core.bot import FortniteBot
    from core.account import PartialEpicAccount, FullEpicAccount
    from fortnite.base import AccountBoundMixin
    from fortnite.stw import SaveTheWorldItem, Survivor, LeadSurvivor

    from discord import Interaction

    FortniteInteraction = Interaction[FortniteBot]

    Account = PartialEpicAccount | FullEpicAccount
    GenericSurvivor = Survivor | LeadSurvivor

    STWFetchable = TypeVar('STWFetchable', bound=SaveTheWorldItem)
    Selectable = TypeVar('Selectable', bound=AccountBoundMixin)

Attributes = dict[str, Any]
Dict = dict[str, Any]
List = list[Dict]
Json = Dict | List

FriendType = Literal['friends', 'incoming', 'outgoing', 'suggested', 'blocklist']

Material = Literal['Crystal', 'Ore']
FortStat = Literal['Fortitude', 'Offense', 'Resistance', 'Tech']
HeroType = Literal['Commando', 'Constructor', 'Outlander', 'Ninja']
SetBonus = Literal[
    'TrapDurability',
    'RangedDamage',
    'MeleeDamage',
    'TrapDamage',
    'AbilityDamage',
    'Fortitude',
    'Resistance',
    'ShieldRegen']
Personality = Literal[
    'Competitive',
    'Cooperative',
    'Adventurous',
    'Dependable',
    'Analytical',
    'Pragmatic',
    'Dreamer',
    'Curious']


account_kwargs = {
    'display': 'Search by Epic display name.',
    'epic_id': 'Search by Epic account ID.',
    'user': 'Search by Discord user.'}

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

resource_categories = {
    'Perk-Up': ['AMP-UP!', 'FIRE-UP!', 'FROST-UP!', 'Uncommon PERK-UP!', 'Rare PERK-UP!', 'Epic PERK-UP!', 'Legendary PERK-UP!'],
    'Re-Perk': ['RE-PERK!', 'Core RE-PERK!'],
    'Evo Materials': ['Pure Drop of Rain', 'Lightning in a Bottle', 'Eye of the Storm', 'Storm Shard'],
    'Manuals': ['Trap Designs', 'Training Manual', 'Weapon Designs'],
    'Superchargers': ['Trap Supercharger', 'Weapon Supercharger', 'Hero Supercharger', 'Survivor Supercharger'],
    'XP': ['Hero XP', 'Survivor XP', 'Schematic XP', 'Venture XP'],
    'Flux': ['Legendary Flux', 'Epic Flux', 'Rare Flux'],
    'Vouchers': ['Weapon Research Voucher', 'Hero Recruitment Voucher'],
    'Currency': ['Gold', 'X-Ray Tickets'],
    'Llamas': ['Mini Reward Llama', 'Upgrade Llama Token', 'Legendary Troll Stash Llama Token']
}

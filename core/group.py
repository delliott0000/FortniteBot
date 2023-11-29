from __future__ import annotations
from typing import TYPE_CHECKING

from collections.abc import Iterable

from core.errors import FortniteException
from fortnite.stw import Survivor
from components.embed import EmbedField, CustomEmbed
from resources.emojis import emojis

from discord import app_commands

if TYPE_CHECKING:
    from core.auth import AuthSession
    from fortnite.stw import Schematic, MissionAlert, SurvivorSquad, Hero
    from resources.extras import Account, GenericSurvivor

    from discord import Colour


class CustomGroup(app_commands.Group):

    @staticmethod
    def heroes_to_fields(
        heroes: Iterable[Hero],
        show_ids: bool = True,
        inline: bool = False
    ) -> Iterable[EmbedField]:
        for hero in heroes:
            hid = f'> {emojis["id"]} **Item ID:** `{hero.item_id}`\n' if show_ids is True else ''
            hero_type = emojis['hero_types'].get(hero.type, '')
            hero_perk = f'> {emojis["hero_perk"]} **Standard Perk:**\n' \
                        f'> **`{hero.support_perk_name}: {hero.support_perk_desc}`**\n' \
                        f'> {emojis["hero_perk"]} **Commander Perk:**\n' \
                        f'> **`{hero.commander_perk_name}: {hero.commander_perk_desc}`**' \
                if show_ids is False else ''

            field = EmbedField(
                name=f'{hero.emoji} {hero_type} {hero.name}',
                value=f'> {emojis["level"]} **Level:** `{hero.level}`\n'
                      f'> {emojis["tiers"][hero.tier][None]} **Tier:** `{hero.tier}`\n'
                      f'> {emojis["power"]} **PL:** `{hero.power_level}`\n'
                      f'{hid}'
                      f'> {emojis["favourite"]} **Favorite:** '
                      f'{emojis["check" if hero.favourite is True else "cross"]}\n'
                      f'{hero_perk}',
                inline=inline)

            yield field

    @staticmethod
    def survivors_to_fields(
        survivors: Iterable[GenericSurvivor],
        show_ids: bool = True,
        inline: bool = False
    ) -> Iterable[EmbedField]:
        for survivor in survivors:
            extras = emojis['set_bonuses'][survivor.set_bonus_type] if isinstance(survivor, Survivor) else \
                emojis['lead_survivors'][survivor.preferred_squad_name]
            sid = f'> {emojis["id"]} **Item ID:** `{survivor.item_id}`\n' if show_ids is True else ''

            field = EmbedField(
                name=f'{survivor.emoji} {emojis["personalities"][survivor.personality]} {extras} {survivor.name}',
                value=f'> {emojis["level"]} **Level:** `{survivor.level}`\n'
                      f'> {emojis["tiers"][survivor.tier][None]} **Tier:** `{survivor.tier}`\n'
                      f'> {emojis["power"]} **PL:** `{survivor.base_power_level}`\n'
                      f'{sid}'
                      f'> {emojis["favourite"]} **Favorite:** '
                      f'{emojis["check" if survivor.favourite is True else "cross"]}',
                inline=inline)

            yield field

    @staticmethod
    def schematics_to_fields(
        schematics: Iterable[Schematic],
        show_ids: bool = True,
        inline: bool = False
    ) -> Iterable[EmbedField]:
        for schematic in schematics:

            perks = f'> {emojis["perk"]} **Perks:** ' \
                    f'{"".join([emojis["perk_rarities"][perk.rarity] for perk in schematic.perks])}\n' \
                if schematic.perks else ''
            sid = f'> {emojis["id"]} **Item ID:** `{schematic.item_id}`\n' if show_ids is True else ''

            field = EmbedField(
                name=f'{schematic.emoji} {schematic.name}',
                value=f'> {emojis["level"]} **Level:** `{schematic.level}`\n'
                      f'> {emojis["tiers"][schematic.tier][schematic.material]} **Tier:** `{schematic.tier}`\n'
                      f'> {emojis["power"]} **PL:** `{schematic.power_level}`\n'
                      f'{perks}'
                      f'{sid}'
                      f'> {emojis["favourite"]} **Favorite:** '
                      f'{emojis["check" if schematic.favourite is True else "cross"]}',
                inline=inline)

            yield field

    @staticmethod
    def mission_alerts_to_fields(
        mission_alerts: Iterable[MissionAlert],
        show_theater: bool = False
    ) -> Iterable[EmbedField]:
        for mission_alert in mission_alerts:

            rewards_str = '\n'.join(
                [f'> {reward.emoji} `{reward.name} x{reward.quantity}`' for reward in mission_alert.alert_rewards])
            theater_str = f'({mission_alert.theater})' if show_theater is True else ''

            field = EmbedField(
                name=f'{emojis["mission_icons"][mission_alert.name]} {mission_alert.name} {theater_str}',
                value=f'> {emojis["power"]} **Power Rating:** `{mission_alert.power}`\n'
                      f'> {emojis["tile_theme"]} **Zone Theme:** `{mission_alert.theme}`\n'
                      f'> {emojis["red_skull"]} **4-Player:** '
                      f'{emojis["check"] if mission_alert.four_player is True else emojis["cross"]}\n'
                      f'> {emojis["loot"]} **Alert Rewards:**\n{rewards_str}',
                inline=False)

            yield field

    def squads_to_embeds(
        self,
        squads: Iterable[SurvivorSquad],
        **kwargs: str | int | Colour
    ) -> list[CustomEmbed]:
        if not squads:
            raise FortniteException('This player does not have any survivor squads.')

        embeds = []

        for squad in squads:

            fort_stats: dict = squad.fort_stats
            fort_type: str = max(fort_stats, key=fort_stats.get)
            points: int = fort_stats.get(fort_type, 0)

            embed = CustomEmbed(
                colour=kwargs.get('colour'),
                description=f'**IGN:** `{squad.account}`\n'
                            f'**{emojis["fort_icons"][fort_type]} {fort_type}:** `+{points}`\n')
            embed.set_author(name=squad.name, icon_url=kwargs.get('icon_url'))
            embed.set_thumbnail(url=emojis['squads'][squad.name])

            survivors = [squad.lead_survivor] if squad.lead_survivor else []
            survivors += squad.survivors
            fields = self.survivors_to_fields(survivors, show_ids=False, inline=True)
            for field in fields:
                embed.append_field(field)

            embeds.append(embed)

        for embed in embeds:
            embed.set_footer(text=f'Page {embeds.index(embed) + 1} of {len(embeds)}')

        return embeds

    @staticmethod
    async def fetch_heroes(
        auth_session: AuthSession,
        account: Account,
        name: str,
        category: app_commands.Choice[str] | None
    ) -> list[Hero]:
        heroes = await account.heroes(auth_session)
        heroes = [hero for hero in heroes if name.lower() in hero.name.lower() and
                  (not category or category.name == hero.type)]

        if not heroes:
            raise FortniteException(f'Hero `{name}` not found.')

        return heroes

    @staticmethod
    async def fetch_survivors(
        auth_session: AuthSession,
        account: Account,
        name: str,
        personality: app_commands.Choice[str] | None
    ) -> list[GenericSurvivor]:
        survivors = await account.survivors(auth_session)
        survivors = [survivor for survivor in survivors if name.lower() in survivor.name.lower() and
                     (not personality or personality.name == survivor.personality)]

        if not survivors:
            raise FortniteException(f'Survivor `{name}` not found.')

        return survivors

    @staticmethod
    async def fetch_schematics(
        auth_session: AuthSession,
        account: Account,
        name: str
    ) -> list[Schematic]:
        schematics = await account.schematics(auth_session)
        schematics = [schematic for schematic in schematics if name.lower() in schematic.name.lower()]

        if not schematics:
            raise FortniteException(f'Schematic `{name}` not found.')

        return schematics

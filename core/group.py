from __future__ import annotations
from typing import TYPE_CHECKING

from core.errors import FortniteException
from fortnite.stw import Survivor
from components.embed import EmbedField
from resources.emojis import emojis

from discord import app_commands

if TYPE_CHECKING:
    from core.auth import AuthSession
    from fortnite.stw import Schematic
    from resources.extras import Account, GenericSurvivor


class CustomGroup(app_commands.Group):

    @staticmethod
    def survivors_to_fields(survivors: list[GenericSurvivor], inline: bool = False) -> list[EmbedField]:
        fields = []

        for survivor in survivors:
            extras = emojis['set_bonuses'][survivor.set_bonus_type] if isinstance(survivor, Survivor) else \
                emojis['lead_survivors'][survivor.preferred_squad_name]

            field = EmbedField(
                name=f'{survivor.emoji} {emojis["personalities"][survivor.personality]} {extras} {survivor.name}',
                value=f'> {emojis["level"]} **Level:** `{survivor.level}`\n'
                      f'> {emojis["tiers"][survivor.tier][None]} **Tier:** `{survivor.tier}`\n'
                      f'> {emojis["power"]} **PL:** `{survivor.base_power_level}`\n'
                      f'> {emojis["id"]} **Item ID:** `{survivor.item_id}`\n'
                      f'> {emojis["favourite"]} **Favorite:** '
                      f'{emojis["check" if survivor.favourite is True else "cross"]}',
                inline=inline)

            fields.append(field)

        return fields

    @staticmethod
    def schematics_to_fields(schematics: list[Schematic], inline: bool = False) -> list[EmbedField]:
        fields = []

        for schematic in schematics:

            perks = f'> {emojis["perk"]} **Perks:** ' \
                    f'{"".join([emojis["perk_rarities"][perk.rarity] for perk in schematic.perks])}\n' \
                if schematic.perks else ''

            field = EmbedField(
                name=f'{schematic.emoji} {schematic.name}',
                value=f'> {emojis["level"]} **Level:** `{schematic.level}`\n'
                      f'> {emojis["tiers"][schematic.tier][schematic.material]} **Tier:** `{schematic.tier}`\n'
                      f'> {emojis["power"]} **PL:** `{schematic.power_level}`\n'
                      f'{perks}'
                      f'> {emojis["id"]} **Item ID:** `{schematic.item_id}`\n'
                      f'> {emojis["favourite"]} **Favorite:** '
                      f'{emojis["check" if schematic.favourite is True else "cross"]}',
                inline=inline)

            fields.append(field)

        return fields

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

from __future__ import annotations

from discord import Embed


class EmbedField:

    __slots__ = (
        'name',
        'value',
        'inline'
    )

    def __init__(self, name: str, value: str, inline: bool) -> None:
        self.name: str = name
        self.value: str = value
        self.inline: bool = inline


class CustomEmbed(Embed):

    def append_field(self, field: EmbedField) -> CustomEmbed:
        return self.add_field(name=field.name, value=field.value, inline=field.inline)

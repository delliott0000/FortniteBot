from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.decorators import FortniteInteraction

from discord import Embed


class EmbedField:

    __slots__ = (
        'name',
        'value',
        'inline'
    )

    def __init__(self, *, name: str, value: str, inline: bool) -> None:
        self.name: str = name
        self.value: str = value
        self.inline: bool = inline


class CustomEmbed(Embed):

    __slots__ = ()

    def __init__(
        self,
        interaction: FortniteInteraction,
        title: str | None = None,
        description: str | None = None
    ) -> None:
        colour = interaction.client.colour(interaction.guild)
        super().__init__(title=title, description=description, colour=colour)

    def append_field(self, field: EmbedField) -> CustomEmbed:
        return self.add_field(name=field.name, value=field.value, inline=field.inline)

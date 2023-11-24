from __future__ import annotations

from abc import ABC
from typing import ClassVar
from urllib.parse import quote


class Route(ABC):

    BASE: ClassVar[str] = ''

    __slots__ = (
        'path',
        'kwargs'
    )

    def __init__(self, path: str, **kwargs: str) -> None:
        if self.BASE == '':
            raise ValueError('Route must have a base.')

        self.path: str = path
        self.kwargs: dict[str, str] = {k: self.quote(v) for k, v in kwargs.items()}

    def __hash__(self) -> int:
        return hash(self.url)

    def __str__(self) -> str:
        return self.url

    def __eq__(self, other: Route) -> bool:
        return isinstance(other, Route) and self.url == other.url

    @staticmethod
    def quote(string: str) -> str:
        string = quote(string)
        string = string.replace('/', '%2F')
        return string

    @property
    def url(self) -> str:
        return self.BASE + self.path.format(**self.kwargs)


class EpicGamesService(Route):

    BASE = 'https://www.epicgames.com'


class AccountService(Route):

    BASE = 'https://account-public-service-prod.ol.epicgames.com'


class FriendsService(Route):

    BASE = 'https://friends-public-service-prod.ol.epicgames.com'


class FortniteService(Route):

    BASE = 'https://fngw-mcp-gc-livefn.ol.epicgames.com'


class CosmeticService(Route):

    BASE = 'https://fortnite-api.com'


class FNCentralService(Route):

    BASE = 'https://fortnitecentral.genxgames.gg'

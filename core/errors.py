from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from resources.extras import Json
    from fortnite.base import BaseEntity

    from aiohttp import ClientResponse


class FortniteException(Exception):

    pass


class HTTPException(FortniteException):

    def __init__(self, response: ClientResponse, data: Json) -> None:
        self.response = response
        self.data = data.copy()

        _error_data: dict = data if isinstance(data, dict) else {}
        self.code: str = data.get('errorCode', 'unknown_error_code')
        self.message: str = data.get('errorMessage', 'An error occurred.')
        self.message_vars: list[str] = data.get('messageVars', [])
        self.originating_service: str | None = data.get('originatingService')
        self.intent: str | None = data.get('intent')

    def __str__(self) -> str:
        return f'{self.response.status} {self.response.reason} - {self.message}'


class FortniteItemException(FortniteException):

    def __init__(self, item: BaseEntity) -> None:
        self.item: BaseEntity = item


class UnknownTemplateID(FortniteItemException):

    def __str__(self) -> str:
        return 'Unknown Template ID: ' + self.item.template_id


class MalformedItemAttributes(FortniteItemException):

    def __str__(self) -> str:
        return 'Malformed item attributes: ' + str(self.item.raw_attributes)


class ItemIsReadOnly(FortniteItemException):

    def __str__(self) -> str:
        return 'Item is not bound to an `AuthSession` so it is read-only'


class ItemIsFavourited(FortniteItemException):

    def __str__(self) -> str:
        return f'Favourite items can not be recycled.'


class InvalidUpgrade(FortniteItemException):

    def __str__(self) -> str:
        return 'An invalid target level/tier was specified.'

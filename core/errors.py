from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fortnite.base import BaseEntity

    from aiohttp import ClientResponse


class FortniteException(Exception):

    pass


class HTTPException(FortniteException):

    def __init__(self, response: ClientResponse, data: dict) -> None:
        self.response = response
        self.data = data

        self.url: str = str(response.url)
        self.method: str = response.method
        self.status: int = response.status
        self.reason: str = response.reason

        self.error_code: str = data.get('errorCode', '[error code not found]')
        self.error_message: str = data.get('errorMessage', '[error message not found]')

    def __str__(self) -> str:
        return f'{self.status} {self.reason} - {self.error_message} ({self.error_code})'


class BadRequest(HTTPException):

    pass


class Unauthorized(HTTPException):

    pass


class Forbidden(HTTPException):

    pass


class NotFound(HTTPException):

    pass


class TooManyRequests(HTTPException):

    pass


class ServerError(HTTPException):

    pass


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

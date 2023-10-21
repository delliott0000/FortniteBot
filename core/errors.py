from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fortnite.base import Attributes, BaseEntity

from aiohttp import ClientResponse


class FortniteException(Exception):

    pass


class HTTPException(FortniteException):

    def __init__(self, resp: ClientResponse, data: dict) -> None:
        self.response = resp
        self.data = data

        self.url: str = str(resp.url)
        self.method: str = resp.method
        self.status: int = resp.status
        self.reason: str = resp.reason

        self.error_code: str = data.get('errorCode', '[error code not found]')
        self.error_message: str = data.get('errorMessage', '[error message not found]')

    def __str__(self) -> str:
        return f'{self.method.upper()} {self.url} responded with {self.status} {self.reason}' \
               f' - {self.error_message} ({self.error_code})'


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

    def __init__(self, item_id: str, template_id: str) -> None:
        self.item_id: str = item_id
        self.template_id: str = template_id

    def __str__(self) -> str:
        return f'Exception raised by item {self.item_id} (TID: {self.template_id})'


class UnknownTemplateID(FortniteItemException):

    def __str__(self) -> str:
        return super().__str__() + ' - Unknown Template ID'


class MalformedItemAttributes(FortniteItemException):

    def __init__(self, item_id: str, template_id: str, attributes: Attributes) -> None:
        super().__init__(item_id, template_id)
        self.attributes: Attributes = attributes.copy()

    def __str__(self) -> str:
        return super().__str__() + ' - Malformed Item Attributes'


class ItemIsReadOnly(FortniteItemException):

    def __init__(self, item: BaseEntity) -> None:
        super().__init__(item.item_id, item.template_id)
        self.item: BaseEntity = item

    def __str__(self) -> str:
        return super().__str__() + ' - Item is not tied to an `AuthSession` so it can not be edited.'

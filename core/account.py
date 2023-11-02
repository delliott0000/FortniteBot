from __future__ import annotations
from typing import TYPE_CHECKING

import logging
from typing import Literal, TypedDict, TypeVar
from weakref import ref, ReferenceType

from core.errors import UnknownTemplateID, MalformedItemAttributes
from fortnite.stw import SaveTheWorldItem, Schematic, Hero

if TYPE_CHECKING:
    from datetime import datetime
    from core.https import _Dict, _List
    from core.auth import AuthSession
    from fortnite.base import Attributes

from dateutil import parser
from core.errors import HTTPException


_STWTypes = TypeVar('_STWTypes', bound=SaveTheWorldItem)

_FriendTypes = Literal['friends', 'incoming', 'outgoing', 'suggested', 'blocklist']


class FriendDict(TypedDict):

    account: PartialEpicAccount
    favorite: bool
    mutual: int | None
    alias: str | None
    note: str | None
    created: datetime | None


class PartialEpicAccount:

    __slots__ = (
        '__weakref__',
        'id',
        'display',
        'raw_attributes',
        '_stw_raw_cache',
        '_stw_obj_cache',
        '_icon_url'
    )

    def __init__(self, auth_session: AuthSession, data: _Dict) -> None:
        self.id: str = data.get('id') or data.get('accountId')
        self.display: str = data.get('displayName', auth_session.bot.UNKNOWN_STR)
        self.raw_attributes: _Dict = data.copy()

        self._stw_raw_cache: _Dict | None = None
        self._stw_obj_cache: _Dict = {}

        self._icon_url: str | None = None

    async def _raw_stw_data(self, _au: AuthSession) -> _Dict:
        if self._stw_raw_cache is None:
            self._stw_raw_cache = await _au.profile_operation(epic_id=self.id)
        return self._stw_raw_cache

    async def _raw_stw_items(self, _au: AuthSession) -> _Dict:
        data = await self._raw_stw_data(_au)
        return data['profileChanges'][0]['profile']['items']

    async def _stw_objects(
        self,
        _au: AuthSession,
        cache_location: str,
        *item_types: tuple[str, type[_STWTypes]]
    ) -> list[_STWTypes]:
        try:
            _return = self._stw_obj_cache[cache_location]
        except KeyError:
            _return = self._stw_obj_cache[cache_location] = []

            raw_items = await self._raw_stw_items(_au)
            for item_id, item_data in raw_items.items():

                template_id: str = item_data['templateId']
                attributes: Attributes = item_data['attributes']

                for item_type in item_types:
                    tid_prefix: str = item_type[0]
                    item_cls = item_type[1]

                    if template_id.startswith(tid_prefix):
                        try:
                            item = item_cls(self, item_id, template_id, attributes)
                        except (UnknownTemplateID, MalformedItemAttributes) as error:
                            logging.error(error)
                            continue

                        _return.append(item)

        return _return

    async def schematics(self, auth_session: AuthSession) -> list[Schematic]:
        schematics = await self._stw_objects(auth_session, 'schematics', ('Schematic:sid', Schematic))
        schematics.sort(key=lambda schematic: schematic.power_level, reverse=True)
        return schematics

    async def heroes(self, auth_session: AuthSession) -> list[Hero]:
        heroes = await self._stw_objects(auth_session, 'heroes', ('Hero:hid', Hero))
        heroes.sort(key=lambda hero: hero.power_level, reverse=True)
        return heroes

    async def icon_url(self, auth_session: AuthSession) -> str | None:
        if self._icon_url is None:
            try:
                data: _Dict = await self._raw_stw_data(auth_session)
                items_data: _Dict = data['profileChanges'][0]['profile']['items']
            except (HTTPException, KeyError):
                return

            for item_id, data in items_data.items():

                try:
                    tid: str = data['templateId']
                    if not tid.startswith('CosmeticLocker'):
                        continue

                    character_id: str = data['attributes']['locker_slots_data']['slots']['Character']['items'][0][16:]

                    http = auth_session.http_client
                    character_data = await http.get(http.COSMETICS_URL.format(character_id))
                    self._icon_url = character_data['data']['images']['icon']
                    break

                except HTTPException:
                    return
                except KeyError:
                    continue

        return self._icon_url


class FullEpicAccount(PartialEpicAccount):

    __slots__ = (
        '_auth_session',
        'display_changes',
        'can_update_display',
        'real_name',
        'language',
        'country',
        'email',
        'verified',
        'failed_logins',
        'tfa_enabled',
        'display_last_updated',
        'date_of_birth',
        'last_login'
    )

    def __init__(self, auth_session: AuthSession, data: _Dict) -> None:
        super().__init__(auth_session, data)
        unknown = auth_session.bot.UNKNOWN_STR

        self._auth_session: ReferenceType[AuthSession] = ref(auth_session)

        self.display_changes: int = data.get('numberOfDisplayNameChanges', 0)
        self.can_update_display: bool | None = data.get('canUpdateDisplayName')

        self.real_name: str = data.get('name', unknown) + ' ' + data.get('lastName', unknown)
        self.language: str = data.get('preferredLanguage', unknown).capitalize()
        self.country: str = data.get('country', unknown)

        self.email: str = data.get('email', unknown)
        self.verified: bool | None = data.get('emailVerified')

        self.failed_logins: int = data.get('failedLoginAttempts', 0)
        self.tfa_enabled: bool | None = data.get('tfaEnabled')

        self.display_last_updated: datetime | None = None
        self.date_of_birth: datetime | None = None
        self.last_login: datetime | None = None

        for __attr in (
            ('display_last_updated', 'lastDisplayNameChange'),
            ('date_of_birth', 'dateOfBirth'),
            ('last_login', 'lastLogin')
        ):
            try:
                self.__setattr__(__attr[0], parser.parse(data.get(__attr[1])))
            except (TypeError, parser.ParserError):
                pass

    @property
    def auth_session(self) -> AuthSession:
        return self._auth_session()

    async def friends_list(self, friend_type: _FriendTypes) -> list[FriendDict]:
        url = self.auth_session.http_client.BASE_FRIENDS_URL + f'/{self.id}/summary'
        data: _Dict = await self.auth_session.access_request('get', url)
        friend_type_data: _List = data[friend_type]

        account_ids: list[str] = [_entry['accountId'] for _entry in friend_type_data]
        accounts = await self.auth_session.fetch_accounts(*account_ids)

        # Fetching accounts doesn't preserve order
        account_ids.sort(key=lambda _id: _id)
        accounts.sort(key=lambda _account: _account.id)

        # Formatting the dictionaries
        for i in range(len(account_ids)):
            entry = friend_type_data[i]

            entry['account'] = accounts[i]
            entry['favorite'] = entry.get('favorite', False)

            for string in 'mutual', 'alias', 'note':
                # Replace any empty strings or missing values with `None`
                entry[string] = entry.get(string) or None

            try:
                entry['created'] = parser.parse(entry.get('created'))
            except (TypeError, parser.ParserError):
                entry['created'] = None

        return friend_type_data

    async def friend(self, account: PartialEpicAccount) -> None:
        url = self.auth_session.http_client.BASE_FRIENDS_URL + f'/{self.id}/friends/{account.id}'
        await self.auth_session.access_request('post', url)

    async def unfriend(self, account: PartialEpicAccount) -> None:
        url = self.auth_session.http_client.BASE_FRIENDS_URL + f'/{self.id}/friends/{account.id}'
        await self.auth_session.access_request('delete', url)

    async def block(self, account: PartialEpicAccount) -> None:
        url = self.auth_session.http_client.BASE_FRIENDS_URL + f'/{self.id}/blocklist/{account.id}'
        await self.auth_session.access_request('post', url)

    async def unblock(self, account: PartialEpicAccount) -> None:
        url = self.auth_session.http_client.BASE_FRIENDS_URL + f'/{self.id}/blocklist/{account.id}'
        await self.auth_session.access_request('delete', url)

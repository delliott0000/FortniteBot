from __future__ import annotations
from typing import TYPE_CHECKING

from datetime import datetime
from weakref import ref, ReferenceType

if TYPE_CHECKING:
    from core.https import _Dict
    from core.auth import AuthSession

from dateutil import parser
from core.errors import HTTPException


class PartialEpicAccount:

    __slots__ = (
        'id',
        'display',
        '_stw_raw_cache',
        '_stw_obj_cache',
        '_btr_raw_cache',
        '_btr_obj_cache',
        '_icon_url'
    )

    def __init__(self, auth_session: AuthSession, data: _Dict) -> None:
        self.id: str = data.get('id') or data.get('accountId')
        self.display: str = data.get('displayName', auth_session.bot.UNKNOWN_STR)

        self._stw_raw_cache: _Dict | None = None
        self._btr_raw_cache: _Dict | None = None

        self._icon_url: str | None = None

    async def raw_stw_data(self, auth_session: AuthSession) -> _Dict:
        if self._stw_raw_cache is None:
            self._stw_raw_cache = await auth_session.profile_operation(
                epic_id=self.id
            )
        return self._stw_raw_cache

    async def raw_btr_data(self, auth_session: AuthSession) -> _Dict:
        if self._btr_raw_cache is None:
            self._btr_raw_cache = await auth_session.profile_operation(
                epic_id=self.id,
                route='client',
                operation='QueryProfile',
                profile_id='athena'
            )
        return self._btr_raw_cache

    async def icon_url(self, auth_session: AuthSession) -> str | None:
        if self._icon_url is None:
            try:
                data: _Dict = await self.raw_btr_data(auth_session)
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

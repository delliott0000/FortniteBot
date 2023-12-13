from __future__ import annotations
from typing import TYPE_CHECKING

from typing import TypedDict
from logging import getLogger
from datetime import datetime, date
from weakref import ref, ReferenceType

from core.route import CosmeticService, FriendsService
from core.errors import HTTPException, UnknownTemplateID, MalformedItemAttributes
from fortnite.stw import Schematic, Survivor, LeadSurvivor, SurvivorSquad, Hero, AccountResource

if TYPE_CHECKING:
    from core.auth import AuthSession
    from resources.extras import Dict, List, STWFetchable, GenericSurvivor, FriendType, Attributes


_logger = getLogger(__name__)


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
        '_br_raw_cache',
        '_icon_url'
    )

    def __init__(self, auth_session: AuthSession, data: Dict) -> None:
        self.id: str = data.get('id') or data.get('accountId')
        self.display: str = data.get('displayName', auth_session.bot.UNKNOWN_STR)
        self.raw_attributes: Dict = data.copy()

        self._stw_raw_cache: Dict | None = None
        self._stw_obj_cache: Dict = {}

        self._br_raw_cache: Dict | None = None

        self._icon_url: str | None = None

    def __hash__(self) -> int:
        return hash(self.id)

    def __str__(self) -> str:
        return self.display

    def __eq__(self, other: PartialEpicAccount) -> bool:
        return isinstance(other, PartialEpicAccount) and self.id == other.id

    async def _raw_stw_data(self, _au: AuthSession) -> Dict:
        if self._stw_raw_cache is None:
            self._stw_raw_cache = await _au.profile_operation(epic_id=self.id)
        return self._stw_raw_cache

    async def _raw_stw_items(self, _au: AuthSession) -> Dict:
        data = await self._raw_stw_data(_au)
        return data['profileChanges'][0]['profile']['items']

    async def _stw_objects(
        self,
        _au: AuthSession,
        cache_location: str,
        *item_types: tuple[str, type[STWFetchable]]
    ) -> list[STWFetchable]:
        try:
            objects = self._stw_obj_cache[cache_location]
        except KeyError:
            objects = self._stw_obj_cache[cache_location] = []

            raw_items = await self._raw_stw_items(_au)
            for item_id, item_data in raw_items.items():

                template_id: str = item_data['templateId']
                attributes: Attributes = item_data['attributes']

                for item_type in item_types:
                    tid_prefix: str = item_type[0]
                    item_cls = item_type[1]

                    if template_id.startswith(tid_prefix):
                        if item_cls is AccountResource:
                            attributes |= {'quantity': item_data.get('quantity', 1)}
                        try:
                            item = item_cls(self, item_id, template_id, attributes)
                        except (UnknownTemplateID, MalformedItemAttributes) as error:
                            _logger.error(error)
                            continue

                        objects.append(item)

        return objects

    async def schematics(self, auth_session: AuthSession) -> list[Schematic]:
        schematics = await self._stw_objects(auth_session, 'schematics', ('Schematic:sid', Schematic))
        schematics.sort(key=lambda schematic: schematic.power_level, reverse=True)
        return schematics

    async def survivors(self, auth_session: AuthSession) -> list[GenericSurvivor]:
        item_types = ('Worker:manager', LeadSurvivor), ('Worker:worker', Survivor)
        survivors = await self._stw_objects(auth_session, 'survivors', *item_types)
        survivors.sort(key=lambda survivor: survivor.base_power_level, reverse=True)
        return survivors

    async def squads(self, auth_session: AuthSession) -> list[SurvivorSquad]:
        try:
            squads = self._stw_obj_cache['squads']
        except KeyError:
            squads = self._stw_obj_cache['squads'] = []
            mapping: dict[str, dict[str, list | LeadSurvivor | None]] = {}

            for survivor in await self.survivors(auth_session):

                _squad_id = survivor.squad_id
                if _squad_id is None:
                    continue

                elif isinstance(survivor, Survivor):
                    try:
                        mapping[_squad_id]['survivors'].append(survivor)
                    except KeyError:
                        mapping[_squad_id] = {'survivors': [survivor], 'lead': None}

                elif isinstance(survivor, LeadSurvivor):
                    try:
                        mapping[_squad_id]['lead'] = survivor
                    except KeyError:
                        mapping[_squad_id] = {'survivors': [], 'lead': survivor}

            for squad_id, squad_composition in mapping.items():
                squad = SurvivorSquad(self, squad_id, squad_composition['lead'], squad_composition['survivors'])
                squads.append(squad)

        return squads

    async def heroes(self, auth_session: AuthSession) -> list[Hero]:
        heroes = await self._stw_objects(auth_session, 'heroes', ('Hero:hid', Hero))
        heroes.sort(key=lambda hero: hero.power_level, reverse=True)
        return heroes

    async def resources(self, auth_session: AuthSession) -> list[AccountResource]:
        resources = await self._stw_objects(auth_session, 'resources', ('AccountResource', AccountResource))
        resources.sort(key=lambda resource: resource.quantity, reverse=True)
        return resources

    async def _raw_br_data(self, _au: AuthSession) -> Dict:
        if self._br_raw_cache is None:
            self._br_raw_cache = await _au.profile_operation(
                epic_id=self.id,
                route='client',
                operation='QueryProfile',
                profile_id='athena'
            )
        return self._br_raw_cache

    async def _raw_br_items(self, _au: AuthSession) -> Dict:
        data = await self._raw_br_data(_au)
        return data['profileChanges'][0]['profile']['items']

    async def icon_url(self, auth_session: AuthSession) -> str | None:
        if self._icon_url is None:
            try:
                items_data = await self._raw_br_items(auth_session)
            except (HTTPException, KeyError):
                return

            for item_id, data in items_data.items():

                try:
                    tid: str = data['templateId']
                    if not tid.startswith('CosmeticLocker'):
                        continue

                    character_id: str = data['attributes']['locker_slots_data']['slots']['Character']['items'][0][16:]

                    http = auth_session.http_client
                    route = CosmeticService('/v2/cosmetics/br/{character_id}', character_id=character_id)
                    character_data = await http.get(route)
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

    def __init__(self, auth_session: AuthSession, data: Dict) -> None:
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

        self.display_last_updated: datetime = datetime.fromisoformat(data.get('lastDisplayNameChange'))
        self.last_login: datetime = datetime.fromisoformat(data.get('lastLogin'))
        self.date_of_birth: date = date.fromisoformat(data.get('dateOfBirth'))

    @property
    def auth_session(self) -> AuthSession:
        return self._auth_session()

    async def friends_list(self, friend_type: FriendType) -> list[FriendDict]:
        route = FriendsService('/friends/api/v1/{account_id}/summary', account_id=self.id)
        data: Dict = await self.auth_session.access_request('get', route)
        friend_type_data: List = data[friend_type]

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
                entry['created'] = datetime.fromisoformat(entry.get('created'))
            except (TypeError, ValueError):
                entry['created'] = None

        return friend_type_data

    async def friend(self, account: PartialEpicAccount) -> None:
        route = FriendsService(
            '/friends/api/v1/{account_id}/friends/{friend_id}',
            account_id=self.id,
            friend_id=account.id)
        await self.auth_session.access_request('post', route)

    async def unfriend(self, account: PartialEpicAccount) -> None:
        route = FriendsService(
            '/friends/api/v1/{account_id}/friends/{friend_id}',
            account_id=self.id,
            friend_id=account.id)
        await self.auth_session.access_request('delete', route)

    async def block(self, account: PartialEpicAccount) -> None:
        route = FriendsService(
            '/friends/api/v1/{account_id}/blocklist/{friend_id}',
            account_id=self.id,
            friend_id=account.id)
        await self.auth_session.access_request('post', route)

    async def unblock(self, account: PartialEpicAccount) -> None:
        route = FriendsService(
            '/friends/api/v1/{account_id}/blocklist/{friend_id}',
            account_id=self.id,
            friend_id=account.id)
        await self.auth_session.access_request('delete', route)

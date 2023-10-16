from __future__ import annotations
from typing import TYPE_CHECKING

import logging
from datetime import datetime
from weakref import ref, ReferenceType

from core.errors import Unauthorized
from core.account import PartialEpicAccount, FullEpicAccount

if TYPE_CHECKING:
    from core.https import FortniteHTTPClient
    from core.bot import FortniteBot

from dateutil import parser


class AuthSession:

    __slots__ = (
        '__weakref__',
        'http_client',
        'bot',
        'discord_id',
        'epic_id',
        'access_token',
        'refresh_token',
        'access_expires',
        'refresh_expires',
        '_killed',
        '_cached_full_account',
        '_cached_full_account_expires'
    )

    def __init__(self, http_client: FortniteHTTPClient, discord_id: int, data: dict) -> None:
        self.http_client: FortniteHTTPClient = http_client
        self.bot: FortniteBot = http_client.bot

        self.discord_id: int = discord_id
        self._renew_data(data)

        # True if session was killed via HTTP
        self._killed: bool = False

        self._cached_full_account: ReferenceType[FullEpicAccount] | None = None
        self._set_cached_account_expiration()

        self.bot.cache_auth_session(self)
        logging.info(f'Auth Session [{self.access_token}] created.')

    def __del__(self) -> None:
        logging.info(f'Auth Session [{self.access_token}] destroyed.')

    @property
    def is_active(self) -> bool:
        return not self._killed and self.access_expires > self.bot.now

    @property
    def is_expired(self) -> bool:
        return self._killed or self.refresh_expires < self.bot.now

    def _renew_data(self, data: dict) -> None:
        self.epic_id: str = data.get('account_id')
        self.access_token: str = data.get('access_token')
        self.refresh_token: str = data.get('refresh_token')
        self.access_expires: datetime = parser.parse(data.get('expires_at'))
        self.refresh_expires: datetime = parser.parse(data.get('refresh_expires_at'))

    def _set_cached_account_expiration(self) -> None:
        self._cached_full_account_expires: datetime = self.bot.now + self.bot.ACCOUNT_CACHE_DURATION

    async def access_request(self, method: str, url: str, retry: bool = False, **kwargs) -> dict:
        headers = {'Authorization': f'bearer {self.access_token}'}

        try:
            return await self.http_client.request(method, url, headers=headers, **kwargs)

        except Unauthorized as unauthorized_error:

            if retry is True or self.is_expired is True:
                raise unauthorized_error

            await self.renew()
            return await self.access_request(method, url, retry=True, **kwargs)

    async def renew(self) -> None:
        # Do nothing if access token is already active
        if self.is_active is True:
            return

        data = await self.http_client.renew_auth_session(self.refresh_token)
        self._renew_data(data)

    async def kill(self) -> None:
        try:
            url = self.http_client.BASE_EPIC_URL + '/oauth/sessions/kill/' + self.access_token
            await self.access_request('delete', url)
        # Session is already expired; do nothing
        except Unauthorized:
            pass
        self._killed = True

    async def account(self) -> FullEpicAccount:
        if self._cached_full_account is None or self._cached_full_account_expires < self.bot.now:
            data = await self.access_request('get', self.http_client.BASE_EPIC_URL + '/public/account/' + self.epic_id)
            account = FullEpicAccount(self, data)
            self._cached_full_account = ref(account)
            self._set_cached_account_expiration()
        return self._cached_full_account()

    async def fetch_account(
            self,
            display: str | None = None,
            account_id: str | None = None
    ) -> PartialEpicAccount:
        account = self.bot.get_partial_account(display=display, account_id=account_id)
        if account is not None:
            return account

        url_formatter = 'displayName/' if account_id is None else ''
        lookup = account_id or display

        data = await self.access_request(
            'get',
            self.http_client.ACCOUNT_REQUESTS_URL.format(url_formatter + lookup)
        )

        account = PartialEpicAccount(self, data)
        self.bot.cache_partial_account(account)

        return account

    async def fetch_accounts(
            self,
            *account_ids: str
    ) -> list[PartialEpicAccount]:
        account_list: list[PartialEpicAccount] = []
        _account_ids: list[str] = list(account_ids)

        for account_id in account_ids:
            account = self.bot.get_partial_account(account_id=account_id)
            if account is not None:
                account_list.append(account)
                _account_ids.remove(account_id)

        if _account_ids:
            data = await self.access_request(
                'get',
                self.http_client.ACCOUNT_REQUESTS_URL.format(''),
                params=[('accountId', _account_id) for _account_id in _account_ids]
            )

            # Note: here `data` is actually a `list[dict]`, not a `dict`
            # To-do: Type-hint improvements on HTTP-related methods
            for entry in data:
                account = PartialEpicAccount(self, entry)
                self.bot.cache_partial_account(account)
                account_list.append(account)

        return account_list

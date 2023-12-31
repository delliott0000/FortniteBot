from __future__ import annotations
from typing import TYPE_CHECKING

from logging import getLogger
from datetime import datetime

from core.errors import HTTPException
from core.account import PartialEpicAccount, FullEpicAccount
from core.route import AccountService, FortniteService

if TYPE_CHECKING:
    from core.https import FortniteHTTPClient
    from core.bot import FortniteBot
    from core.route import Route
    from resources.extras import Dict, List, Json


_logger = getLogger(__name__)


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
        '_account',
        '_cached_full_account_expires'
    )

    def __init__(self, http_client: FortniteHTTPClient, discord_id: int, data: Dict) -> None:
        self.http_client: FortniteHTTPClient = http_client
        self.bot: FortniteBot = http_client.bot

        self.discord_id: int = discord_id
        self._renew_data(data)

        # True if session was killed via HTTP
        self._killed: bool = False

        self._account: FullEpicAccount | None = None
        self._set_cached_account_expiration()

        self.bot.cache_auth_session(self)

        self._log_action('initialised')

    def __del__(self) -> None:
        self._log_action('destroyed')

    @property
    def is_active(self) -> bool:
        return not self._killed and self.access_expires > self.bot.now

    @property
    def is_expired(self) -> bool:
        return self._killed or self.refresh_expires < self.bot.now

    def _log_action(self, action: str) -> None:
        _logger.info('Auth session %s %s. (Account ID: %s)', self.access_token, action, self.epic_id)

    def _renew_data(self, data: Dict) -> None:
        self.epic_id: str = data.get('account_id')
        self.access_token: str = data.get('access_token')
        self.refresh_token: str = data.get('refresh_token')
        self.access_expires: datetime = datetime.fromisoformat(data.get('expires_at'))
        self.refresh_expires: datetime = datetime.fromisoformat(data.get('refresh_expires_at'))

    def _set_cached_account_expiration(self) -> None:
        self._cached_full_account_expires: datetime = self.bot.now + self.bot.ACCOUNT_CACHE_DURATION

    def manage_cached_account(self) -> None:
        if self._cached_full_account_expires < self.bot.now:
            self._account = None

    async def renew(self, *, force: bool = False) -> Dict | None:
        if self.is_active is True and force is False:
            return

        data = await self.http_client.renew_auth_session(self.refresh_token)

        self._renew_data(data)
        self._log_action('renewed')

        return data

    async def access_request(self, method: str, route: Route, retry: bool = False, **kwargs) -> Json:
        headers = kwargs.pop('headers', None) or {'Authorization': f'bearer {self.access_token}'}

        try:
            return await self.http_client.request(method, route, headers=headers, **kwargs)

        except HTTPException as error:

            if error.response.status != 401 or retry is True or self.is_expired is True:
                raise error

            await self.renew()
            return await self.access_request(method, route, retry=True, headers=headers, **kwargs)

    async def kill(self) -> None:
        try:
            route = AccountService(
                '/account/api/oauth/sessions/kill/{access_token}',
                access_token=self.access_token)
            await self.access_request('delete', route)

        except HTTPException:
            pass

        else:
            self._log_action('killed')

        self._killed = True

    async def account(self) -> FullEpicAccount:
        if self._account is None or self._cached_full_account_expires < self.bot.now:
            route = AccountService('/account/api/public/account/{account_id}', account_id=self.epic_id)
            data: Dict = await self.access_request('get', route)
            self._account = FullEpicAccount(self, data)
            self._set_cached_account_expiration()
        return self._account

    async def fetch_account(
        self,
        display: str | None = None,
        account_id: str | None = None
    ) -> PartialEpicAccount:
        account = self.bot.get_partial_account(display=display, account_id=account_id)
        if account is not None:
            return account

        if display is not None:
            route = AccountService('/account/api/public/account/displayName/{display}', display=display)
        else:
            route = AccountService('/account/api/public/account/{account_id}', account_id=account_id)

        data: Dict = await self.access_request('get', route)

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

            _account_ids_chunks: list[list[str]] = [_account_ids[i:i + 100] for i in range(0, len(_account_ids), 100)]
            route = AccountService('/account/api/public/account')

            for _account_ids_chunk in _account_ids_chunks:

                data: List = await self.access_request(
                    'get',
                    route,
                    params=[('accountId', _account_id) for _account_id in _account_ids_chunk]
                )

                for entry in data:
                    account = PartialEpicAccount(self, entry)
                    self.bot.cache_partial_account(account)
                    account_list.append(account)

        return account_list

    async def profile_operation(
        self,
        method: str = 'post',
        epic_id: str | None = None,
        route: str = 'public',
        operation: str = 'QueryPublicProfile',
        profile_id: str = 'campaign',
        json: dict | None = None
    ) -> Json:
        epic_id = epic_id or self.epic_id
        json = json or {}

        route = FortniteService(
            '/fortnite/api/game/v2/profile/{account_id}/{route}/{operation}?profileId={profile_id}',
            account_id=epic_id,
            route=route,
            operation=operation,
            profile_id=profile_id)

        return await self.access_request(method, route, json=json)

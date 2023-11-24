from __future__ import annotations
from typing import TYPE_CHECKING

from collections.abc import Coroutine
from dataclasses import dataclass
from urllib.parse import quote
from logging import getLogger
from base64 import b64encode
from typing import ClassVar
from asyncio import sleep
from time import time
from abc import ABC

from core.auth import AuthSession
from core.errors import HTTPException

from aiohttp import ClientSession, ClientResponseError
from aiohttp.helpers import sentinel

if TYPE_CHECKING:
    from typing import Self, Any
    from types import TracebackType

    from core.bot import FortniteBot
    from resources.extras import Dict, Json

    from aiohttp import BaseConnector, ClientTimeout, ClientResponse


_logger = getLogger(__name__)


@dataclass(kw_only=True, slots=True, weakref_slot=True)
class HTTPRetryConfig:

    max_retries: int = 5
    max_wait_time: float = 65.0

    handle_ratelimits: bool = True
    max_retry_after: float = 60.0

    handle_backoffs: bool = True
    backoff_factor: float = 1.5
    backoff_start: float = 1.0
    backoff_cap: float = 20


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


class FortniteHTTPClient:

    URL = Route | str

    # Base URLs for various Epic Games HTTP services
    BASE_EPIC_URL: str = 'https://account-public-service-prod.ol.epicgames.com/account/api'
    BASE_FORT_URL: str = 'https://fortnite-public-service-prod11.ol.epicgames.com/fortnite/api'
    BASE_FRIENDS_URL: str = 'https://friends-public-service-prod.ol.epicgames.com/friends/api/v1'

    ACCOUNT_REQUESTS_URL: str = BASE_EPIC_URL + '/public/account/{0}'
    PROFILE_REQUESTS_URL: str = BASE_FORT_URL + '/game/v2/profile/{0}/{1}/{2}?profileId={3}'

    # Miscellaneous URL used to get in-game cosmetics data from an item ID
    # Not a part of Epic Games' API
    COSMETICS_URL: str = 'https://fortnite-api.com/v2/cosmetics/br/{0}'

    # Used to fetch the current day's Mission Alerts plus extra related information
    MISSIONS_URL: str = 'https://fngw-mcp-gc-livefn.ol.epicgames.com/fortnite/api/game/v2/world/info'
    FNC_BASE_URL: str = 'https://fortnitecentral.genxgames.gg/api/v1/export?path='

    __slots__ = (
        'bot',
        'retry_config',
        'connector',
        'timeout',
        '_id',
        '_secret',
        '__session'
    )

    def __init__(
        self,
        bot: FortniteBot,
        *,
        retry_config: HTTPRetryConfig | None = None,
        connector: BaseConnector | None = None,
        timeout: ClientTimeout | None = None
    ) -> None:
        self.bot: FortniteBot = bot
        self.retry_config: HTTPRetryConfig = retry_config or HTTPRetryConfig()
        self.connector: BaseConnector | None = connector
        self.timeout: ClientTimeout | None = timeout

        self._id: str = 'ec684b8c687f479fadea3cb2ad83f5c6'
        self._secret: str = 'e1f31c211f28413186262d37a13fc84d'

        self.__session: ClientSession | None = None

    async def __aenter__(self) -> Self:
        await self.create_connection()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException],
        exc_val: BaseException,
        exc_tb: TracebackType
    ) -> None:
        await self.close_connection()

    @property
    def is_open(self) -> bool:
        return self.__session is not None and not self.__session.closed

    async def create_connection(self) -> None:
        self.__session = ClientSession(
            connector=self.connector,
            connector_owner=self.connector is None,
            timeout=self.timeout or sentinel
        )

    async def close_connection(self) -> None:
        if self.__session is not None:
            await self.__session.close()

    @staticmethod
    async def response_to_json(response: ClientResponse) -> Json:
        try:
            return await response.json()
        except ClientResponseError:
            # This should only happen if we receive an empty response from Epic Games.
            return {}

    @staticmethod
    def get_retry_after(error: HTTPException) -> int | None:
        retry_after = error.response.headers.get('Retry-After')
        if retry_after is not None:
            return int(retry_after)

        try:
            return int(error.message_vars[0])
        except (IndexError, TypeError, ValueError):
            return

    async def make_request(self, method: str, raw_url: str, **kwargs: Any) -> Json:
        if self.is_open is False:
            raise RuntimeError('HTTP session is closed.')

        pre_time = time()
        async with self.__session.request(method, raw_url, **kwargs) as response:
            _logger.info(
                '%s %s returned %s %s in %.3fs',
                method.upper(),
                raw_url,
                response.status,
                response.reason,
                time() - pre_time
            )

            data = await self.response_to_json(response)

            if 200 <= response.status < 400:
                return data

            raise HTTPException(response, data)

    async def request(self, method: str, route: URL, **kwargs: Any) -> Json:
        url = str(route)
        config = self.retry_config

        tries = 0
        total_slept = 0
        backoff = config.backoff_start

        while True:
            tries += 1
            sleep_time = 0

            try:
                return await self.make_request(method, url, **kwargs)

            except HTTPException as error:
                if tries >= config.max_retries:
                    raise error

                if error.code == 'errors.com.epicgames.common.throttled' or error.response.status == 429:
                    retry_after = self.get_retry_after(error)

                    if retry_after is not None:
                        if config.handle_ratelimits is True and retry_after <= config.max_retry_after:
                            sleep_time = retry_after

                    else:
                        backoff *= config.backoff_factor
                        if config.handle_backoffs is True and backoff <= config.backoff_cap:
                            sleep_time = backoff

                elif error.code == 'errors.com.epicgames.common.server_error' or \
                        error.code == 'errors.com.epicgames.common.concurrent_modification_error' or \
                        error.response.status >= 500:
                    sleep_time = 2 * (tries - 1) + 0.5

                if sleep_time > 0:
                    total_slept += sleep_time
                    if total_slept > config.max_wait_time:
                        raise error

                    _logger.debug(
                        'Retrying %s %s in %.3fs...',
                        method.upper(),
                        url,
                        sleep_time
                    )

                    await sleep(sleep_time)
                    continue

                raise error

    def get(self, route: URL, **kwargs: Any) -> Coroutine[Any, Any, Json]:
        return self.request('get', route, **kwargs)

    def put(self, route: URL, **kwargs: Any) -> Coroutine[Any, Any, Json]:
        return self.request('put', route, **kwargs)

    def post(self, route: URL, **kwargs: Any) -> Coroutine[Any, Any, Json]:
        return self.request('post', route, **kwargs)

    def patch(self, route: URL, **kwargs: Any) -> Coroutine[Any, Any, Json]:
        return self.request('patch', route, **kwargs)

    def delete(self, route: URL, **kwargs: Any) -> Coroutine[Any, Any, Json]:
        return self.request('delete', route, **kwargs)

    @property
    def user_auth_path(self) -> EpicGamesService:
        return EpicGamesService('/id/api/redirect?clientId={client_id}&responseType=code', client_id=self._id)

    @property
    def auth_exchange_path(self) -> AccountService:
        return AccountService('/account/api/oauth/token')

    @property
    def auth_exchange_secret(self) -> str:
        return b64encode(f'{self._id}:{self._secret}'.encode()).decode()

    async def renew_auth_session(self, refresh_token: str) -> Dict:
        return await self.post(
            self.auth_exchange_path,
            headers={
                'Content-Type':
                    'application/x-www-form-urlencoded',
                'Authorization':
                    f'basic {self.auth_exchange_secret}'
            },
            data={
                'grant_type':
                    'refresh_token',
                'refresh_token':
                    refresh_token
            }
        )

    async def create_auth_session(self, auth_code: str, discord_id: int) -> AuthSession:
        data: Dict = await self.post(
            self.auth_exchange_path,
            headers={
                'Content-Type':
                    'application/x-www-form-urlencoded',
                'Authorization':
                    f'basic {self.auth_exchange_secret}'
            },
            data={
                'grant_type':
                    'authorization_code',
                'code':
                    auth_code
            }
        )
        return AuthSession(self, discord_id, data)

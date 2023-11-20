from __future__ import annotations
from typing import TYPE_CHECKING

from collections.abc import Coroutine
from logging import getLogger
from base64 import b64encode
from asyncio import sleep

from core.auth import AuthSession
from core.errors import (
    HTTPException,
    BadRequest,
    Unauthorized,
    Forbidden,
    NotFound,
    TooManyRequests,
    ServerError
)

from aiohttp import ClientSession, ClientResponseError
from aiohttp.helpers import sentinel

if TYPE_CHECKING:
    from typing import Self, Any
    from types import TracebackType

    from core.bot import FortniteBot
    from resources.extras import Dict, Json

    from aiohttp import BaseConnector, ClientTimeout, ClientResponse


_logger = getLogger(__name__)


async def response_to_json(resp: ClientResponse) -> Json:
    try:
        return await resp.json()
    except ClientResponseError:
        # This should only happen if we receive an empty response from Epic Games.
        return {}


class FortniteHTTPClient:

    REQUEST_RETRY_LIMIT: int = 5

    # ID and secret for the official Fortnite PC game client
    CLIENT_ID: str = 'ec684b8c687f479fadea3cb2ad83f5c6'
    CLIENT_SECRET: str = 'e1f31c211f28413186262d37a13fc84d'

    # URL visited by the user in their browser to obtain an authorization code
    USER_AUTH_URL: str = f'https://www.epicgames.com/id/api/redirect?clientId={CLIENT_ID}&responseType=code'

    # Base URLs for various Epic Games HTTP services
    BASE_EPIC_URL: str = 'https://account-public-service-prod.ol.epicgames.com/account/api'
    BASE_FORT_URL: str = 'https://fortnite-public-service-prod11.ol.epicgames.com/fortnite/api'
    BASE_FRIENDS_URL: str = 'https://friends-public-service-prod.ol.epicgames.com/friends/api/v1'

    ACCOUNT_REQUESTS_URL: str = BASE_EPIC_URL + '/public/account/{0}'
    PROFILE_REQUESTS_URL: str = BASE_FORT_URL + '/game/v2/profile/{0}/{1}/{2}?profileId={3}'

    # Used to exchange the user's authorization code for a session, and to keep existing sessions alive
    AUTH_EXCHANGE_URL: str = BASE_EPIC_URL + '/oauth/token'
    AUTH_EXCHANGE_SECRET: str = b64encode(f'{CLIENT_ID}:{CLIENT_SECRET}'.encode()).decode()

    # Miscellaneous URL used to get in-game cosmetics data from an item ID
    # Not a part of Epic Games' API
    COSMETICS_URL: str = 'https://fortnite-api.com/v2/cosmetics/br/{0}'

    # Used to fetch the current day's Mission Alerts plus extra related information
    MISSIONS_URL: str = 'https://fngw-mcp-gc-livefn.ol.epicgames.com/fortnite/api/game/v2/world/info'
    FNC_BASE_URL: str = 'https://fortnitecentral.genxgames.gg/api/v1/export?path='

    __slots__ = (
        'bot',
        'connector',
        'timeout',
        '__session'
    )

    def __init__(
        self,
        bot: FortniteBot,
        *,
        connector: BaseConnector | None = None,
        timeout: ClientTimeout | None = None
    ) -> None:
        self.bot: FortniteBot = bot
        self.connector: BaseConnector | None = connector
        self.timeout: ClientTimeout | None = timeout

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

    async def request(self, method: str, url: str, retries: int = -1, **kwargs) -> Json:
        if self.is_open is False:
            raise RuntimeError('HTTP session is closed.')

        async with self.__session.request(method, url, **kwargs) as resp:
            _logger.info(f'({resp.status}) {method.upper() + "      "[:6 - len(method)]} {url}')

            data = await response_to_json(resp)

            if 200 <= resp.status < 300:
                return data

            elif resp.status == 429 and retries < self.REQUEST_RETRY_LIMIT:
                retries += 1
                retry_after = 2 ** retries

                _logger.warning(f'We are being rate limited. Retrying in {retry_after} seconds...')
                await sleep(retry_after)

                return await self.request(method, url, retries=retries, **kwargs)

            elif resp.status == 400:
                cls = BadRequest
            elif resp.status == 401:
                cls = Unauthorized
            elif resp.status == 403:
                cls = Forbidden
            elif resp.status == 404:
                cls = NotFound
            elif resp.status == 429:
                cls = TooManyRequests
            elif resp.status >= 500:
                cls = ServerError
            else:
                cls = HTTPException

            raise cls(resp, data)

    def get(self, url: str, **kwargs) -> Coroutine[Any, Any, Json]:
        return self.request('get', url, **kwargs)

    def put(self, url: str, **kwargs) -> Coroutine[Any, Any, Json]:
        return self.request('put', url, **kwargs)

    def post(self, url: str, **kwargs) -> Coroutine[Any, Any, Json]:
        return self.request('post', url, **kwargs)

    def patch(self, url: str, **kwargs) -> Coroutine[Any, Any, Json]:
        return self.request('patch', url, **kwargs)

    def delete(self, url: str, **kwargs) -> Coroutine[Any, Any, Json]:
        return self.request('delete', url, **kwargs)

    async def renew_auth_session(self, refresh_token: str) -> Dict:
        return await self.post(
            self.AUTH_EXCHANGE_URL,
            headers={
                'Content-Type':
                    'application/x-www-form-urlencoded',
                'Authorization':
                    f'basic {self.AUTH_EXCHANGE_SECRET}'
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
            self.AUTH_EXCHANGE_URL,
            headers={
                'Content-Type':
                    'application/x-www-form-urlencoded',
                'Authorization':
                    f'basic {self.AUTH_EXCHANGE_SECRET}'
            },
            data={
                'grant_type':
                    'authorization_code',
                'code':
                    auth_code
            }
        )
        return AuthSession(self, discord_id, data)

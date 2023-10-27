from __future__ import annotations
from typing import TYPE_CHECKING

import logging
import asyncio
from typing import Any
from base64 import b64encode

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

if TYPE_CHECKING:
    from core.bot import FortniteBot

from aiohttp import (
    ClientResponseError,
    ClientResponse,
    ClientSession
)


_Dict = dict[str, Any]
_List = list[_Dict]
_Json = _Dict | _List


async def response_to_json(resp: ClientResponse) -> _Json:
    try:
        return await resp.json()
    except ClientResponseError:
        # Theoretically this should only happen if we receive an empty response from Epic Games.
        # In which case it is appropriate to return an empty dictionary.
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

    __slots__ = (
        'bot',
        '_session'
    )

    def __init__(self, bot: FortniteBot) -> None:
        self.bot: FortniteBot = bot
        self._session: ClientSession | None = None

    async def __aenter__(self) -> FortniteHTTPClient:
        self._session = ClientSession()
        return self

    async def __aexit__(self, *_) -> bool:
        await self._session.close()
        return False

    async def request(self, method: str, url: str, retries: int = -1, **kwargs) -> _Json:
        async with self._session.request(method, url, **kwargs) as resp:
            logging.info(f'({resp.status}) {method.upper() + "      "[:6 - len(method)]} {url}')

            data = await response_to_json(resp)

            if 200 <= resp.status < 300:
                return data

            elif resp.status == 429 and retries < self.REQUEST_RETRY_LIMIT:
                retries += 1
                retry_after = 2 ** retries

                logging.warning(f'We are being rate limited. Retrying in {retry_after} seconds...')
                await asyncio.sleep(retry_after)

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

    async def get(self, url: str, **kwargs) -> _Json:
        return await self.request('get', url, **kwargs)

    async def put(self, url: str, **kwargs) -> _Json:
        return await self.request('put', url, **kwargs)

    async def post(self, url: str, **kwargs) -> _Json:
        return await self.request('post', url, **kwargs)

    async def patch(self, url: str, **kwargs) -> _Json:
        return await self.request('patch', url, **kwargs)

    async def delete(self, url: str, **kwargs) -> _Json:
        return await self.request('delete', url, **kwargs)

    async def renew_auth_session(self, refresh_token: str) -> _Dict:
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
        data: _Dict = await self.post(
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

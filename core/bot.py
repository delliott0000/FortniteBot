from __future__ import annotations
from typing import TYPE_CHECKING

import os
import logging
import asyncio
from datetime import datetime, timedelta

from resources.config import TOKEN, OWNER_IDS
from core.errors import FortniteException, HTTPException
from core.cache import PartialAccountCacheEntry
from core.https import FortniteHTTPClient
from core.database import DatabaseClient

if TYPE_CHECKING:
    from core.auth import AuthSession
    from core.account import PartialEpicAccount

from discord.ext import commands, tasks
from discord import (
    __version__ as __discord__,
    Intents,
    app_commands,
    LoginFailure,
    PrivilegedIntentsRequired
)


if __discord__ != '2.3.2':
    logging.fatal('The incorrect version of discord.py has been installed.')
    logging.fatal('Current Version: {}'.format(__discord__))
    logging.fatal('Required: 2.3.2')

    raise SystemExit()


class FortniteBot(commands.Bot):

    ACCOUNT_CACHE_DURATION: timedelta = timedelta(seconds=900)
    UNKNOWN_STR: str = '[UNKNOWN]'

    def __init__(self) -> None:

        intents = Intents.none()
        intents.guilds = True

        super().__init__(
            owner_ids=OWNER_IDS,
            help_command=None,
            command_prefix='',
            intents=intents,
        )

        self.app_commands: list[app_commands.AppCommand] = []

        self.http_client: FortniteHTTPClient | None = None
        self.database_client: DatabaseClient | None = None

        self._partial_account_cache: dict[str, PartialAccountCacheEntry] = {}
        self._auth_session_cache: dict[int, AuthSession] = {}

        self._tasks: tuple[tasks.Loop, ...] = (self.manage_partial_cache, self.manage_auth_cache)

    async def __aexit__(self, *_) -> None:
        for auth_session in self._auth_session_cache.values():
            try:
                await auth_session.kill()
            except HTTPException:
                continue
        return await super().__aexit__(*_)

    @property
    def now(self) -> datetime:
        return datetime.utcnow()

    def get_partial_account(
            self,
            display: str | None = None,
            account_id: str | None = None
    ) -> PartialEpicAccount | None:
        lookup = account_id or display
        if lookup is None:
            raise FortniteException('An Epic ID or display name is required.')

        entry = self._partial_account_cache.get(lookup)
        if entry is not None:
            return entry.get('account')

    def cache_partial_account(self, account: PartialEpicAccount) -> None:
        if account.id not in self._partial_account_cache:
            self._partial_account_cache[account.id] = PartialAccountCacheEntry(
                account=account,
                expires=self.now + self.ACCOUNT_CACHE_DURATION
            )
            if account.display is not self.UNKNOWN_STR:
                self._partial_account_cache[account.display] = self._partial_account_cache[account.id]

    def remove_partial_account(self, account_id: str) -> None:
        try:
            cache_entry = self._partial_account_cache.pop(account_id)
        except KeyError:
            return
        try:
            self._partial_account_cache.pop(cache_entry['account'].display)
        except (KeyError, AttributeError):
            return

    @tasks.loop(minutes=1)
    async def manage_partial_cache(self) -> None:
        account_ids: list[str] = []

        for account_id, cache_entry in self._partial_account_cache.items():
            if cache_entry['expires'] <= self.now:
                account_ids.append(account_id)

        for _account_id in account_ids:
            self.remove_partial_account(_account_id)

    def get_auth_session(self, discord_id: int) -> AuthSession | None:
        return self._auth_session_cache.get(discord_id)

    def cache_auth_session(self, auth_session: AuthSession) -> None:
        if auth_session.discord_id not in self._auth_session_cache:
            self._auth_session_cache[auth_session.discord_id] = auth_session

    def remove_auth_session(self, discord_id: int) -> None:
        try:
            self._auth_session_cache.pop(discord_id)
        except KeyError:
            pass

    @tasks.loop(minutes=1)
    async def manage_auth_cache(self) -> None:
        for discord_id, auth_session in self._auth_session_cache.items():
            if auth_session.refresh_expires - self.ACCOUNT_CACHE_DURATION <= self.now:

                try:
                    await auth_session.renew()
                    logging.info(f'Auth Session [{auth_session.access_token}] renewed.')
                    continue
                except HTTPException:
                    await auth_session.kill()
                    self.remove_auth_session(discord_id)

    async def setup_hook(self) -> None:
        user = self.user
        owners = [(await self.fetch_user(user_id)).name for user_id in self.owner_ids]

        logging.info(f'Logging in as {user} (ID: {user.id})...')
        logging.info(f'Owner(s): {" ".join(owners)}')

        logging.info('Syncing app commands...')
        self.app_commands = await self.tree.sync()
        logging.info('Done!')

        for task in self._tasks:
            task.add_exception_type(Exception)
            task.start()

    def run_bot(self) -> None:

        async def _runner():
            async with FortniteHTTPClient(self) as self.http_client, DatabaseClient(self) as self.database_client:
                async with self:
                    for filename in os.listdir('./ext'):
                        if filename.endswith('.py'):
                            try:
                                await self.load_extension(f'ext.{filename[:-3]}')
                            except (commands.ExtensionFailed, commands.NoEntryPointError) as extension_error:
                                logging.error(f'Extension {filename} could not be loaded: {extension_error}')
                    try:
                        await self.start(TOKEN)
                    except LoginFailure:
                        logging.fatal('Invalid token passed.')
                    except PrivilegedIntentsRequired:
                        logging.fatal('Intents are being requested that have not been enabled in the developer portal.')

        try:
            asyncio.run(_runner())
        except (KeyboardInterrupt, SystemExit):
            logging.info('Received signal to terminate bot and event loop.')
        finally:
            logging.info('Done. Have a nice day!')

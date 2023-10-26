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
from components.embed import CustomEmbed

if TYPE_CHECKING:
    from core.auth import AuthSession
    from core.account import PartialEpicAccount
    from core.decorators import FortniteInteraction

from discord.ui import View
from discord.ext import commands, tasks
from discord.utils import MISSING, _MissingSentinel
from discord import (
    __version__ as __discord__,
    Guild,
    Colour,
    Intents,
    app_commands,
    LoginFailure,
    InteractionResponded,
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

        self._tasks: tuple[tasks.Loop, ...] = (self.manage_partial_cache, self.manage_auth_cache, self.manage_data_base)

    async def __aexit__(self, *_) -> None:
        for task in self._tasks:
            task.cancel()
            task.clear_exception_types()
        for auth_session in self._auth_session_cache.values():
            try:
                await auth_session.kill()
            except HTTPException:
                continue
        return await super().__aexit__(*_)

    @property
    def now(self) -> datetime:
        return datetime.utcnow()

    @staticmethod
    def colour(guild: Guild | None) -> Colour:
        try:
            return guild.me.colour
        except AttributeError:
            return Colour(16777215)

    async def send_response(
        self,
        interaction: FortniteInteraction,
        message: str,
        colour: Colour | None = None,
        view: View | _MissingSentinel = MISSING
    ) -> None:
        embed = CustomEmbed(description=message, colour=colour or self.colour(interaction.guild))
        try:
            # noinspection PyUnresolvedReferences
            await interaction.response.send_message(embed=embed, view=view)
        except InteractionResponded:
            await interaction.followup.send(embed=embed, view=view)

    async def bad_response(
        self,
        interaction: FortniteInteraction,
        message: str,
        view: View | _MissingSentinel = MISSING
    ) -> None:
        await self.send_response(interaction, f'❌ {message}', colour=Colour.red(), view=view)

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

    @tasks.loop(minutes=1)
    async def manage_data_base(self) -> None:
        now = self.now
        for discord_id, premium_until in await self.database_client.get_premium_states():
            if premium_until < now:
                await self.database_client.expire_premium(discord_id)

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

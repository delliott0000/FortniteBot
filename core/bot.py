from __future__ import annotations
from typing import TYPE_CHECKING

import os
import logging
import asyncio
from datetime import datetime, timedelta, time

from resources.config import TOKEN, OWNER_IDS
from resources.lookup import lookup
from core.errors import FortniteException, HTTPException
from core.https import FortniteHTTPClient
from core.database import DatabaseClient
from core.tree import CustomTree
from components.embed import CustomEmbed
from fortnite.stw import MissionAlert, MissionAlertReward

from discord.ui import View
from discord.ext import commands, tasks
from discord.utils import MISSING, _MissingSentinel
from discord import (
    __version__ as __discord__,
    Colour,
    Intents,
    app_commands,
    LoginFailure,
    InteractionResponded,
    PrivilegedIntentsRequired
)

if TYPE_CHECKING:
    from core.auth import AuthSession
    from core.account import PartialEpicAccount
    from core.cache import PartialAccountCacheEntry
    from components.embed import EmbedField
    from resources.extras import FortniteInteraction, Dict, List

    from discord import User, Guild


if __discord__ != '2.3.2':
    logging.fatal('The incorrect version of discord.py has been installed.')
    logging.fatal('Current Version: {}'.format(__discord__))
    logging.fatal('Required: 2.3.2')

    raise SystemExit()


class FortniteBot(commands.Bot):

    ACCOUNT_CACHE_DURATION: timedelta = timedelta(seconds=900)
    DURATION_CONVERTER_MAP: dict[str, int] = {'s': 1, 'm': 60, 'h': 3600, 'd': 86400, 'w': 604800, 'y': 31536000}
    MISSION_REFRESH_TIME: time = time(minute=1)
    UNKNOWN_STR: str = '[UNKNOWN]'

    def __init__(self) -> None:

        intents = Intents.none()
        intents.guilds = True

        super().__init__(
            owner_ids=OWNER_IDS,
            help_command=None,
            command_prefix=None,
            intents=intents,
            tree_cls=CustomTree
        )

        self.app_commands: list[app_commands.AppCommand] = []

        self.http_client: FortniteHTTPClient | None = None
        self.database_client: DatabaseClient | None = None

        self._partial_account_cache: dict[str, PartialAccountCacheEntry] = {}
        self._auth_session_cache: dict[int, AuthSession] = {}

        self._tasks: tuple[tasks.Loop, ...] = (
            self.manage_partial_cache,
            self.manage_auth_cache,
            self.manage_data_base,
            self.refresh_mission_alerts)

        self._mission_alerts: list[MissionAlert] = []

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

    @staticmethod
    def _new_embed(**kwargs: str | Colour) -> CustomEmbed:
        return CustomEmbed(
            title=kwargs.get('title'),
            description=kwargs.get('description'),
            colour=kwargs.get('colour'))

    def string_to_duration(self, string: str) -> timedelta:
        try:
            n = int(string[:-1])
            multiplier = self.DURATION_CONVERTER_MAP[string[-1].lower()]
        except (ValueError, KeyError):
            raise ValueError('An invalid duration was specified.')
        return timedelta(seconds=n * multiplier)

    def fields_to_embeds(self, fields: list[EmbedField], **kwargs: str | int | Colour) -> list[CustomEmbed]:
        embed_list: list[CustomEmbed] = [self._new_embed(**kwargs)]

        for field in fields:
            if len(embed_list[-1].fields) >= kwargs.get('field_limit', 6):
                embed_list.append(self._new_embed(**kwargs))
            embed_list[-1].append_field(field)

        for embed in embed_list:
            embed.set_footer(text=f'Page {embed_list.index(embed) + 1} of {len(embed_list)}')

        author_name = kwargs.get('author_name')
        if author_name is not None:
            for embed in embed_list:
                embed.set_author(name=author_name, icon_url=kwargs.get('author_icon'))

        return embed_list

    async def send_response(
        self,
        interaction: FortniteInteraction,
        message: str,
        colour: Colour | None = None,
        view: View | _MissingSentinel = MISSING,
        ephemeral: bool = True
    ) -> None:
        embed = CustomEmbed(description=message, colour=colour or self.colour(interaction.guild))
        try:
            # noinspection PyUnresolvedReferences
            await interaction.response.send_message(embed=embed, view=view, ephemeral=ephemeral)
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
        account_lookup = account_id or display
        if account_lookup is None:
            raise FortniteException('An Epic ID or display name is required.')

        entry = self._partial_account_cache.get(account_lookup)
        if entry is not None:
            return entry.get('account')

    def cache_partial_account(self, account: PartialEpicAccount) -> None:
        if account.id not in self._partial_account_cache:
            self._partial_account_cache[account.id] = dict(
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
        dead_session_discord_ids: list[int] = []

        for discord_id, auth_session in self._auth_session_cache.items():
            auth_session.manage_cached_account()

            if auth_session.refresh_expires - self.ACCOUNT_CACHE_DURATION <= self.now:
                try:
                    await auth_session.renew()
                    logging.info(f'Auth Session [{auth_session.access_token}] renewed.')
                    continue
                except HTTPException:
                    logging.info(f'Auth Session [{auth_session.access_token}] could not be renewed. Ending session...')
                    await auth_session.kill()
                    dead_session_discord_ids.append(discord_id)

        for _id in dead_session_discord_ids:
            self.remove_auth_session(_id)

    def discord_id_from_account_id(self, account_id: str) -> int | None:
        for discord_id, auth_session in self._auth_session_cache.items():
            if auth_session.epic_id == account_id:
                return discord_id

    async def account_from_discord_id(self, discord_id: int) -> PartialEpicAccount:
        auth_session = self.get_auth_session(discord_id)
        if auth_session is None:
            raise FortniteException(f'<@{discord_id}> is not logged in with {self.user.name}.')
        return await auth_session.fetch_account(account_id=auth_session.epic_id)

    async def account_from_kwargs(
        self,
        auth_session: AuthSession,
        display: str | None = None,
        epic_id: str | None = None,
        user: User | None = None
    ) -> PartialEpicAccount:
        if user is not None:
            return await self.account_from_discord_id(user.id)
        else:
            return await auth_session.fetch_account(display=display, account_id=epic_id)

    @tasks.loop(minutes=1)
    async def manage_data_base(self) -> None:
        for discord_id, premium_until in await self.database_client.get_premium_states():
            if premium_until < self.now:
                await self.database_client.expire_premium(discord_id)

    async def mission_alerts(self) -> list[MissionAlert]:
        if not self._mission_alerts:
            await self.refresh_mission_alerts()
        return self._mission_alerts

    @tasks.loop(time=MISSION_REFRESH_TIME)
    async def refresh_mission_alerts(self) -> None:
        self._mission_alerts: list[MissionAlert] = []
        _temp_fnc_cache: Dict = {}

        logging.info('Fetching new Mission Alerts...')

        for auth_session in self._auth_session_cache.values():
            try:
                data: Dict = await auth_session.access_request('get', self.http_client.MISSIONS_URL)
                break
            except HTTPException:
                continue
        else:
            logging.error('Unable to fetch today\'s Mission Alerts, postponing...')
            return

        theaters: List = data.get('theaters')
        missions: List = data.get('missions')
        alerts: List = data.get('missionAlerts')

        path: str = '/Game/Balance/DataTables/GameDifficultyGrowthBounds.GameDifficultyGrowthBounds'
        theater_data: Dict = await self.http_client.get(self.http_client.FNC_BASE_URL + path)

        async def _add_mission_alert(i: int, theater: Dict) -> None:

            theater_id: str = theater.get('theaterId')
            for _theater in theaters:
                if _theater.get('uniqueId') == theater_id:
                    theater_name: str = _theater.get('displayName', {}).get('en', 'Unknown Theater')
                    break
            else:
                theater_name: str = 'Unknown Theater'

            for available_alert in theater.get('availableMissionAlerts'):
                available_alert: Dict

                tile_index: int = available_alert.get('tileIndex', 0)
                alert_rewards_data: List = available_alert.get('missionAlertRewards', {}).get('items', [])

                tile_theme_path: str = data['theaters'][i]['tiles'][tile_index]['zoneTheme']
                _tile_theme_url: str = self.http_client.FNC_BASE_URL + tile_theme_path.split('.')[0]

                tile_theme_data: Dict
                try:
                    tile_theme_data = _temp_fnc_cache[_tile_theme_url]
                except KeyError:
                    tile_theme_data = _temp_fnc_cache[_tile_theme_url] = await self.http_client.get(_tile_theme_url)

                try:
                    tile_theme_name: str = tile_theme_data['jsonOutput'][1]['Properties']['ZoneName']['sourceString']
                except (KeyError, IndexError):
                    tile_theme_name: str = 'Unknown Tile Theme Name'

                for mission in missions[i].get('availableMissions', {}):
                    mission: Dict

                    if mission.get('tileIndex') == tile_index:
                        __theater: str = mission.get('missionDifficultyInfo', {}).get('rowName')
                        generator: str = mission.get('missionGenerator')

                        for mission_name in lookup['Missions']:
                            mission_name: str

                            if mission_name in generator:
                                name = lookup['Missions'][mission_name]
                                break
                        else:
                            name = 'Unknown Mission'

                        try:
                            power_data: str = \
                                theater_data['jsonOutput'][0]['Rows'][__theater]['ThreatDisplayName']['sourceString']
                        except (KeyError, IndexError):
                            power_data: str = '0'

                        alert_rewards = [MissionAlertReward(reward['itemType'], reward)
                                         for reward in alert_rewards_data]
                        mission_alert = MissionAlert(name, tile_theme_name, theater_name, power_data, alert_rewards)

                        self._mission_alerts.append(mission_alert)
                        break

        add_mission_tasks = [_add_mission_alert(_i, _theater) for _i, _theater in enumerate(alerts)]
        await asyncio.gather(*add_mission_tasks)

        logging.info('Mission Alerts fetched successfully.')

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

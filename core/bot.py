import os
import logging
import asyncio

from resources.config import TOKEN, OWNER_IDS
from core.https import FortniteHTTPClient
from core.database import DatabaseClient

from discord.ext import commands
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

    async def setup_hook(self) -> None:
        user = self.user
        owners = [(await self.fetch_user(user_id)).name for user_id in self.owner_ids]

        logging.info(f'Logging in as {user} (ID: {user.id})...')
        logging.info(f'Owner(s): {" ".join(owners)}')

        logging.info('Syncing app commands...')
        '''self.app_commands = await self.tree.sync()'''
        logging.info('Done!')

    def run_bot(self) -> None:

        async def _runner():
            async with self, FortniteHTTPClient(self) as self.http_client, DatabaseClient(self) as self.database_client:
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

from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.bot import FortniteBot

from aiosqlite import (
    connect,
    Connection
)


class DatabaseClient:

    FORMAT: str = \
        'CREATE TABLE IF NOT EXISTS user_data (' \
        'discord_id INTEGER, '                   \
        'blacklisted INTEGER, '                  \
        'premium INTEGER, '                      \
        'premium_until INTEGER'                  \
        ')'

    __slots__ = (
        'bot',
        'connection'
    )

    def __init__(self, bot: FortniteBot) -> None:
        self.bot: FortniteBot = bot
        self.connection: Connection | None = None

    async def __aenter__(self) -> DatabaseClient:
        self.connection = await connect('data.db')
        await self.connection.execute('PRAGMA journal_mode=wal')
        await self.connection.execute(self.FORMAT)
        await self.connection.commit()
        return self

    async def __aexit__(self, *_) -> bool:
        await self.connection.commit()
        await self.connection.close()
        return False

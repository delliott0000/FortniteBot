from __future__ import annotations
from typing import TYPE_CHECKING

from datetime import datetime, timedelta
from collections.abc import AsyncIterable

from aiosqlite import connect

if TYPE_CHECKING:
    from typing import ClassVar, Self
    from types import TracebackType

    from core.bot import FortniteBot

    from aiosqlite import Connection, Cursor


class DatabaseClient:

    FIELDS: ClassVar[tuple[str, ...]] = ('blacklisted', 'premium_until')
    FORMAT: ClassVar[str] = \
        'CREATE TABLE IF NOT EXISTS user_data (' \
        'discord_id INTEGER, '                   \
        'blacklisted INTEGER, '                  \
        'premium_until INTEGER'                  \
        ')'
    INSERT: ClassVar[str] = \
        'INSERT INTO user_data (' \
        'discord_id, '            \
        'blacklisted, '           \
        'premium_until'           \
        ') VALUES (?, ?, ?)'

    __slots__ = (
        'bot',
        '__connection'
    )

    def __init__(self, bot: FortniteBot) -> None:
        self.bot: FortniteBot = bot
        self.__connection: Connection | None = None

    async def __aenter__(self) -> Self:
        self.__connection = await connect('data.db')
        await self.__connection.execute('PRAGMA journal_mode=wal')
        await self.__connection.execute(self.FORMAT)
        await self.__connection.commit()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None
    ) -> None:
        await self.__connection.commit()
        await self.__connection.close()

    @staticmethod
    def _int_to_datetime(integer: int) -> datetime:
        return datetime.fromtimestamp(integer)

    async def _insert(self, discord_id: int) -> None:
        await self.__connection.execute(self.INSERT, (discord_id, 0, 0))
        await self.__connection.commit()

    async def _get_value(self, discord_id: int, value: str) -> int:
        if value not in self.FIELDS:
            raise ValueError(f'Value must be one of the following: {", ".join(self.FIELDS)}')

        cursor: Cursor = await self.__connection.execute(
            f'SELECT {value} FROM user_data WHERE discord_id = ?',
            (discord_id, )
        )
        row = await cursor.fetchone()

        try:
            return row[0]
        except TypeError:
            await self._insert(discord_id)
            return 0

    async def is_blacklisted(self, discord_id: int) -> bool:
        value = await self._get_value(discord_id, 'blacklisted')
        return bool(value)

    async def is_premium(self, discord_id: int) -> bool:
        value = await self._get_value(discord_id, 'premium_until')
        return bool(value)

    async def premium_until(self, discord_id: int) -> datetime | None:
        value = await self._get_value(discord_id, 'premium_until')
        if value:
            return self._int_to_datetime(value)

    async def toggle_blacklist(self, discord_id: int) -> bool:
        new_value = not await self.is_blacklisted(discord_id)
        await self.__connection.execute(
            'UPDATE user_data SET blacklisted = ? WHERE discord_id = ?',
            (new_value, discord_id)
        )
        await self.__connection.commit()
        return new_value

    async def add_premium(self, discord_id: int, duration: timedelta) -> datetime:
        until = (await self.premium_until(discord_id) or self.bot.now) + duration
        await self.__connection.execute(
            'UPDATE user_data SET premium_until = ? WHERE discord_id = ?',
            (round(until.timestamp()), discord_id)
        )
        await self.__connection.commit()
        return until

    async def get_premium_states(self) -> AsyncIterable[tuple[int, datetime]]:
        async with self.__connection.execute(
                'SELECT discord_id, premium_until FROM user_data WHERE premium_until != 0'
        ) as cursor:
            async for record in cursor:
                yield record[0], self._int_to_datetime(record[1])

    async def expire_premium(self, discord_id: int) -> None:
        await self.__connection.execute(
            'UPDATE user_data SET premium_until = ? WHERE discord_id = ?',
            (0, discord_id)
        )
        await self.__connection.commit()

from __future__ import annotations

from typing import TYPE_CHECKING, Callable, Union

if TYPE_CHECKING:
    from pajbot.bot import Bot
    from pajbot.managers.redis import RedisType

    from psycopg2 import cursor as Psycopg2Cursor


class Revision:
    def __init__(self, id: int, name: str, up_action: Callable[[Union[Psycopg2Cursor, RedisType], Bot], None]) -> None:
        self.id = id
        self.name = name
        self.up_action = up_action

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pajbot.bot import Bot
    from redis import Redis


def up(redis: Redis, bot: Bot) -> None:
    redis.delete(f"{bot.streamer.login}:viewer_data")

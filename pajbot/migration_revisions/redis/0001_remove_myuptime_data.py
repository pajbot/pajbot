from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pajbot.bot import Bot
    from pajbot.managers.redis import RedisType


def up(redis: RedisType, bot: Bot) -> None:
    redis.delete(f"{bot.streamer}:viewer_data")

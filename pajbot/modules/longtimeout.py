from __future__ import annotations

from typing import TYPE_CHECKING, Optional

import datetime
import logging
import math

from pajbot import utils
from pajbot.managers.adminlog import AdminLogManager
from pajbot.managers.db import DBManager
from pajbot.managers.handler import HandlerManager
from pajbot.models.command import Command, CommandExample
from pajbot.models.user import User
from pajbot.modules import BaseModule

import pytimeparse
from requests import HTTPError

if TYPE_CHECKING:
    from pajbot.bot import Bot

log = logging.getLogger(__name__)


# 14d
TWITCH_MAX_TIMEOUT_SECONDS = 1209600

CHECK_INTERVAL = datetime.timedelta(seconds=30)
REFRESH_THRESHOLD = datetime.timedelta(minutes=5)


def format_timeout_end(long_timeout_end: datetime.datetime) -> str:
    return long_timeout_end.replace(microsecond=0).isoformat()


def long_timeout_reason(long_timeout_end: datetime.datetime) -> str:
    return f"Long timeout active until {format_timeout_end(long_timeout_end)}"


def apply_long_timeout(bot: Bot, user: User, long_timeout_end: datetime.datetime) -> None:
    duration = get_long_timeout_duration_seconds(long_timeout_end, utils.now())
    if duration <= 0:
        return

    bot.timeout(user, duration, reason=long_timeout_reason(long_timeout_end))


def parse_long_timeout_end(value: str, now: datetime.datetime) -> Optional[datetime.datetime]:
    duration_seconds = pytimeparse.parse(value)
    if duration_seconds is not None:
        if duration_seconds <= 0:
            return None

        return now + datetime.timedelta(seconds=math.ceil(duration_seconds))

    normalized_value = value.strip()
    if normalized_value.endswith("Z"):
        normalized_value = normalized_value[:-1] + "+00:00"

    try:
        long_timeout_end = datetime.datetime.fromisoformat(normalized_value)
    except ValueError:
        return None

    if long_timeout_end.tzinfo is None:
        long_timeout_end = long_timeout_end.replace(tzinfo=datetime.timezone.utc)

    return long_timeout_end.astimezone(datetime.timezone.utc)


def parse_twitch_timeout_end(value: str) -> Optional[datetime.datetime]:
    return parse_long_timeout_end(value, datetime.datetime.min.replace(tzinfo=datetime.timezone.utc))


def get_long_timeout_duration_seconds(long_timeout_end: datetime.datetime, now: datetime.datetime) -> int:
    remaining_seconds = math.ceil((long_timeout_end - now).total_seconds())
    if remaining_seconds <= 0:
        return 0

    return min(remaining_seconds, TWITCH_MAX_TIMEOUT_SECONDS)


def should_refresh_long_timeout(bot: Bot, user: User, long_timeout_end: datetime.datetime) -> bool:
    try:
        ban_data = bot.twitch_helix_api.get_banned_user(bot.streamer.id, bot.streamer_access_token_manager, user.id)
    except HTTPError as e:
        if e.response is None:
            raise e

        log.error(f"Failed to fetch long timeout state for user {user.id}: {e} - {e.response.text}")
        return False

    if ban_data is None or not ban_data.expires_at:
        return True

    current_timeout_end = parse_twitch_timeout_end(ban_data.expires_at)
    if current_timeout_end is None:
        return True

    return current_timeout_end <= utils.now() + REFRESH_THRESHOLD


class LongTimeoutModule(BaseModule):
    ID = __name__.split(".")[-1]
    NAME = "Long Timeout"
    DESCRIPTION = "Keep a user timed out until a future time"
    CATEGORY = "Moderation"
    ENABLED_DEFAULT = False

    def __init__(self, bot, config=None) -> None:
        super().__init__(bot, config=config)
        self.last_long_timeout_check: datetime.datetime = datetime.datetime.min.replace(tzinfo=datetime.timezone.utc)

    def long_timeout_command(self, bot: Bot, source: User, message: str, **rest) -> bool:
        if not message:
            bot.whisper(source, "Usage: !longtimeout USERNAME 60d")
            return False

        msg_split = message.split(" ", 2)
        if len(msg_split) < 2:
            bot.whisper(source, "Usage: !longtimeout USERNAME 60d")
            return False

        username = msg_split[0]
        now = utils.now()
        long_timeout_end = parse_long_timeout_end(msg_split[1], now)
        if long_timeout_end is None or long_timeout_end <= now:
            bot.whisper(
                source,
                "Invalid timeout target. Use a duration or ISO-8601 timestamp (e.g. 60d or 2018-06-04T12:34:56Z)",
            )
            return False

        with DBManager.create_session_scope() as db_session:
            user = User.find_or_create_from_user_input(db_session, bot.twitch_helix_api, username)
            if user is None:
                bot.whisper(source, "No user with that name found.")
                return False

            if user.banned:
                bot.whisper(source, "This user is permabanned already.")
                return False

            user.long_timeout_end = long_timeout_end

            apply_long_timeout(bot, user, long_timeout_end)

            log_msg = f"{user} will be kept timed out until {format_timeout_end(long_timeout_end)}"
            bot.whisper(source, log_msg)
            AdminLogManager.add_entry("Long timeout added", source, log_msg)

        return True

    def unlong_timeout_command(self, bot: Bot, source: User, message: str, **rest) -> bool:
        if not message:
            bot.whisper(source, "Usage: !unlongtimeout USERNAME")
            return False

        username = message.split(" ")[0]
        with DBManager.create_session_scope() as db_session:
            user = User.find_by_user_input(db_session, username)
            if user is None:
                bot.whisper(source, "No user with that name found.")
                return False

            if user.long_timeout_end is None:
                bot.whisper(source, "This user does not have a long timeout.")
                return False

            was_timed_out = user.timed_out
            user.long_timeout_end = None

            if was_timed_out:
                bot.untimeout(user)

            log_msg = f"{user} will no longer be kept timed out"
            bot.whisper(source, log_msg)
            AdminLogManager.add_entry("Long timeout removed", source, log_msg)

        return True

    def on_message(self, source: User, whisper: bool, **rest) -> bool:
        if whisper:
            return True

        if source.long_timeout_end is None:
            return True

        if source.long_timeout_end <= utils.now():
            # Timeout of the user has expired
            source.long_timeout_end = None
            return True

        if self.bot is not None:
            apply_long_timeout(self.bot, source, source.long_timeout_end)

        return True

    def on_tick(self, **rest) -> bool:
        if self.bot is None:
            return True

        now = utils.now()
        if now - self.last_long_timeout_check < CHECK_INTERVAL:
            return True

        self.last_long_timeout_check = now

        with DBManager.create_session_scope() as db_session:
            users = db_session.query(User).filter(User.long_timeout_end.is_not(None)).all()
            for user in users:
                if user.long_timeout_end is None:
                    log.error("long_timeout_end was None despite our query - what's happening?? {user:?}")
                    continue

                if user.long_timeout_end <= now:
                    user.long_timeout_end = None
                    continue

                if should_refresh_long_timeout(self.bot, user, user.long_timeout_end):
                    apply_long_timeout(self.bot, user, user.long_timeout_end)

        return True

    def load_commands(self, **options) -> None:
        self.commands["longtimeout"] = Command.raw_command(
            self.long_timeout_command,
            level=500,
            description="Keep a user timed out until a future time",
            examples=[
                CommandExample(
                    None,
                    "Keep a user timed out for 60 days",
                    chat="mod:!longtimeout pajlada 60d\nbot>mod:pajlada will be kept timed out until 2026-08-01T12:00:00+00:00",
                    description="The bot re-applies the timeout if it gets removed before the target time.",
                ).parse()
            ],
        )
        self.commands["unlongtimeout"] = Command.raw_command(
            self.unlong_timeout_command,
            level=500,
            description="Stop keeping a user timed out",
            examples=[
                CommandExample(
                    None,
                    "Remove a long timeout",
                    chat="mod:!unlongtimeout pajlada\nbot>mod:pajlada will no longer be kept timed out",
                    description="The bot stops re-applying the timeout and removes the current timeout if it is still active.",
                ).parse()
            ],
        )

    def enable(self, bot: Bot | None) -> None:
        self.bot = bot
        HandlerManager.add_handler("on_message", self.on_message, priority=200, run_if_propagation_stopped=True)
        HandlerManager.add_handler("on_tick", self.on_tick)

    def disable(self, bot: Bot | None) -> None:
        HandlerManager.remove_handler("on_message", self.on_message)
        HandlerManager.remove_handler("on_tick", self.on_tick)

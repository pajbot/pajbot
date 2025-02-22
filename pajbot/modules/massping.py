import logging
import re
from datetime import timedelta
from typing import Any
import weakref

from pajbot.managers.db import DBManager
from pajbot.managers.handler import HandlerManager, HandlerResponse, ResponseMeta
from pajbot.message_event import MessageEvent
from pajbot.models.emote import EmoteInstance, EmoteInstanceCountMap
from pajbot.models.user import User
from pajbot.modules import BaseModule, ModuleSetting

from sqlalchemy import and_, or_
from sqlalchemy.sql.functions import count, func

log = logging.getLogger(__name__)

USERNAME_IN_MESSAGE_PATTERN = re.compile("[A-Za-z0-9_]{4,}")


class MassPingProtectionModule(BaseModule):
    ID = __name__.split(".")[-1]
    NAME = "Mass Ping Protection"
    DESCRIPTION = "Times out users who post messages that mention too many users at once."
    CATEGORY = "Moderation"
    SETTINGS = [
        ModuleSetting(
            key="moderation_action",
            label="Moderation action to apply",
            type="options",
            required=True,
            default="Timeout",
            options=["Timeout", "Delete"],
        ),
        ModuleSetting(
            key="stream_status",
            label="Allow mass pings while the stream is:",
            type="options",
            required=True,
            default="Neither offline nor online",
            options=["Online", "Offline", "Neither offline nor online"],
        ),
        ModuleSetting(
            key="max_ping_count",
            label="Maximum number of pings allowed in each message",
            type="number",
            required=True,
            placeholder="",
            default=5,
            constraints={"min_value": 3, "max_value": 100},
        ),
        ModuleSetting(
            key="timeout_length_base",
            label="Base Timeout length (seconds)",
            type="number",
            required=True,
            placeholder="",
            default=120,
            constraints={"min_value": 1, "max_value": 1209600},
        ),
        ModuleSetting(
            key="extra_timeout_length_per_ping",
            label="Timeout length per extra (disallowed extra) ping in the message (seconds)",
            type="number",
            required=True,
            placeholder="",
            default=30,
            constraints={"min_value": 0, "max_value": 1209600},
        ),
        ModuleSetting(
            key="bypass_level",
            label="Level to bypass module",
            type="number",
            required=True,
            placeholder="",
            default=420,
            constraints={"min_value": 100, "max_value": 2000},
        ),
        ModuleSetting(
            key="timeout_reason",
            label="Timeout Reason",
            type="text",
            required=False,
            placeholder="",
            default="Too many users pinged in message",
            constraints={},
        ),
        ModuleSetting(
            key="disable_warnings",
            label="Disable warning timeouts",
            type="boolean",
            required=True,
            default=False,
        ),
    ]

    @staticmethod
    def count_known_users(usernames: set[str]) -> int:
        if len(usernames) < 1:
            return 0
        with DBManager.create_session_scope() as db_session:
            # quick EXPLAIN ANALYZE for this query:
            #
            # pajbot=# EXPLAIN ANALYZE SELECT count(*) AS count_1
            # FROM "user"
            # WHERE ("user".login IN ('randers', 'lul', 'xd', 'penis', 'asd', 'hello', 'world') OR lower("user".name) IN ('randers', 'lul', 'xd', 'penis', 'asd', 'hello', 'world')) AND "user".last_seen IS NOT NULL AND now() - "user".last_seen <= make_interval(weeks := 2);
            #                                                                              QUERY PLAN
            # --------------------------------------------------------------------------------------------------------------------------------------------------------------------
            #  Aggregate  (cost=37.45..37.46 rows=1 width=8) (actual time=0.113..0.113 rows=1 loops=1)
            #    ->  Bitmap Heap Scan on "user"  (cost=21.53..37.43 rows=5 width=0) (actual time=0.110..0.110 rows=1 loops=1)
            #          Recheck Cond: ((login = ANY ('{randers,lul,xd,penis,asd,hello,world}'::text[])) OR (lower(name) = ANY ('{randers,lul,xd,penis,asd,hello,world}'::text[])))
            #          Filter: ((last_seen IS NOT NULL) AND ((now() - last_seen) <= '14 days'::interval))
            #          Heap Blocks: exact=6
            #          ->  BitmapOr  (cost=21.53..21.53 rows=14 width=0) (actual time=0.101..0.101 rows=0 loops=1)
            #                ->  Bitmap Index Scan on user_login_idx  (cost=0.00..10.76 rows=7 width=0) (actual time=0.054..0.054 rows=1 loops=1)
            #                      Index Cond: (login = ANY ('{randers,lul,xd,penis,asd,hello,world}'::text[]))
            #                ->  Bitmap Index Scan on user_lower_idx  (cost=0.00..10.76 rows=7 width=0) (actual time=0.046..0.047 rows=6 loops=1)
            #                      Index Cond: (lower(name) = ANY ('{randers,lul,xd,penis,asd,hello,world}'::text[]))
            #  Planning Time: 0.092 ms
            #  Execution Time: 0.140 ms
            # (12 rows)

            return (
                db_session.query(User)
                .with_entities(count())
                .filter(or_(User.login.in_(usernames), func.lower(User.name).in_(usernames)))
                .filter(and_(User.last_seen.isnot(None), (func.now() - User.last_seen) <= timedelta(weeks=2)))
                .scalar()
            )

    @staticmethod
    def count_pings(message: str, source: User, emote_instances: list[EmoteInstance]) -> int:
        potential_users = set()

        for match in USERNAME_IN_MESSAGE_PATTERN.finditer(message):
            matched_part = match.group()
            start_idx = match.start()
            end_idx = match.end()

            potential_emote = next((e for e in emote_instances if e.start == start_idx and e.end == end_idx), None)
            # this "username" is an emote. skip
            if potential_emote is not None:
                continue

            matched_part = matched_part.lower()

            # this is the sending user. We allow people to "ping" themselves
            if matched_part == source.login or matched_part == source.name.lower():
                continue

            potential_users.add(matched_part)

        # check how many of the words in `potential_users` refer to known users
        # (i.e. we have seen this username before & user was recently seen in chat)
        return MassPingProtectionModule.count_known_users(potential_users)

    def determine_timeout_length(self, message: str, source: User, emote_instances: list[EmoteInstance]) -> int:
        ping_count = MassPingProtectionModule.count_pings(message, source, emote_instances)
        pings_too_many = ping_count - self.settings["max_ping_count"]

        if pings_too_many <= 0:
            return 0

        return self.settings["timeout_length_base"] + self.settings["extra_timeout_length_per_ping"] * pings_too_many

    def check_message(self, message: str, source: User) -> int:
        if self.bot is None:
            log.warning("massping.check_message called with no Bot")
            return 0

        emote_instances, _ = self.bot.emote_manager.parse_all_emotes(message)

        # returns False if message is good,
        # True if message is bad.
        return self.determine_timeout_length(message, source, emote_instances) > 0

    async def on_message(
        self,
        source: User,
        message: str,
        emote_instances: list[EmoteInstance],
        emote_counts: EmoteInstanceCountMap,
        is_whisper: bool,
        urls: list[str],
        msg_id: str | None,
        event: MessageEvent,
        meta: ResponseMeta,
    ) -> HandlerResponse:
        if self.bot is None:
            log.warning("on_message failed because bot is None")
            return HandlerResponse.null()

        if msg_id is None:
            return HandlerResponse.null()

        if is_whisper:
            return HandlerResponse.null()

        if source.level >= self.settings["bypass_level"] or source.moderator is True:
            return HandlerResponse.null()

        if self.settings["stream_status"] == "Online" and self.bot.is_online:
            return HandlerResponse.null()

        if self.settings["stream_status"] == "Offline" and not self.bot.is_online:
            return HandlerResponse.null()

        timeout_duration = self.determine_timeout_length(message, source, emote_instances)

        if timeout_duration <= 0:
            return HandlerResponse.null()

        return HandlerResponse.do_delete_or_timeout(
            source.id,
            self.settings["moderation_action"],
            msg_id,
            timeout_duration,
            self.settings["timeout_reason"],
            disable_warnings=self.settings["disable_warnings"],
        )

    def enable(self, bot) -> None:
        if bot:
            HandlerManager.register_on_message(self.on_message, priority=140)

    def disable(self, bot) -> None:
        if bot:
            HandlerManager.unregister_on_message(self.on_message)

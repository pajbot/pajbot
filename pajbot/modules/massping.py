import logging
import re
from datetime import timedelta

from sqlalchemy import and_, or_
from sqlalchemy.sql.functions import count, func

from pajbot.managers.db import DBManager
from pajbot.managers.handler import HandlerManager
from pajbot.models.user import User
from pajbot.modules import BaseModule
from pajbot.modules import ModuleSetting

log = logging.getLogger(__name__)

USERNAME_IN_MESSAGE_PATTERN = re.compile("[A-Za-z0-9_]{4,}")


class MassPingProtectionModule(BaseModule):

    ID = __name__.split(".")[-1]
    NAME = "Mass Ping Protection"
    DESCRIPTION = "Times out users who post messages that mention too many users at once."
    CATEGORY = "Moderation"
    SETTINGS = [
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
            constraints={"min_value": 30, "max_value": 3600},
        ),
        ModuleSetting(
            key="extra_timeout_length_per_ping",
            label="Timeout length per extra (disallowed extra) ping in the message (seconds)",
            type="number",
            required=True,
            placeholder="",
            default=30,
            constraints={"min_value": 0, "max_value": 600},
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
            key="whisper_offenders",
            label="Send offenders a whisper explaining the timeout",
            type="boolean",
            required=True,
            default=True,
        ),
        ModuleSetting(
            key="whisper_timeout_reason",
            label="Whisper Timeout Reason | Available arguments: {timeout_duration}",
            type="text",
            required=False,
            placeholder="",
            default="You have been timed out for {timeout_duration} seconds because your message mentioned too many users at once.",
            constraints={},
        ),
    ]

    @staticmethod
    def count_known_users(usernames):
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
    def count_pings(message, source, emote_instances):
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

    def determine_timeout_length(self, message, source, emote_instances):
        ping_count = MassPingProtectionModule.count_pings(message, source, emote_instances)
        pings_too_many = ping_count - self.settings["max_ping_count"]

        if pings_too_many <= 0:
            return 0

        return self.settings["timeout_length_base"] + self.settings["extra_timeout_length_per_ping"] * pings_too_many

    def check_message(self, message, source):
        emote_instances, _ = self.bot.emote_manager.parse_all_emotes(message)

        # returns False if message is good,
        # True if message is bad.
        return self.determine_timeout_length(message, source, emote_instances) > 0

    def on_message(self, source, message, emote_instances, **rest):
        if source.level >= self.settings["bypass_level"] or source.moderator is True:
            return

        if self.settings["stream_status"] == "Online" and self.bot.is_online:
            return

        if self.settings["stream_status"] == "Offline" and not self.bot.is_online:
            return

        timeout_duration = self.determine_timeout_length(message, source, emote_instances)

        if timeout_duration <= 0:
            return

        self.bot.timeout(source, timeout_duration, reason=self.settings["timeout_reason"])

        if self.settings["whisper_offenders"]:
            self.bot.whisper(source, self.settings["whisper_timeout_reason"].format(timeout_duration=timeout_duration))

        return False

    def enable(self, bot):
        HandlerManager.add_handler("on_message", self.on_message, priority=150, run_if_propagation_stopped=True)

    def disable(self, bot):
        HandlerManager.remove_handler("on_message", self.on_message)

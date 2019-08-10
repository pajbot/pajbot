import logging
import re

from pajbot.managers.handler import HandlerManager
from pajbot.managers.redis import RedisManager
from pajbot.modules import BaseModule
from pajbot.modules import ModuleSetting
from pajbot.streamhelper import StreamHelper

log = logging.getLogger(__name__)

username_in_message_pattern = re.compile("[A-Za-z0-9_]{4,}")


class MassPingProtectionModule(BaseModule):

    ID = __name__.split(".")[-1]
    NAME = "Mass Ping Protection"
    DESCRIPTION = "Times out users who post messages that mention too many users at once."
    CATEGORY = "Filter"
    SETTINGS = [
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
            key="whisper_offenders",
            label="Send offenders a whisper explaining the timeout",
            type="boolean",
            required=True,
            default=True,
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
    ]

    def __init__(self, bot):
        super().__init__(bot)

    @staticmethod
    def is_known_user(username):
        streamer = StreamHelper.get_streamer()
        return RedisManager.get().hexists("{streamer}:users:last_seen".format(streamer=streamer), username)

    @staticmethod
    def count_pings(message, source, emote_instances):
        pings = set()

        for match in username_in_message_pattern.finditer(message):
            matched_part = match.group()
            start_idx = match.start()
            end_idx = match.end()

            potential_emote = next((e for e in emote_instances if e.start == start_idx and e.end == end_idx), None)
            # this "username" is an emote. skip
            if potential_emote is not None:
                continue

            matched_part = matched_part.lower()

            # this is the sending user. We allow people to "ping" themselves
            if matched_part == source.username or matched_part == source.username_raw.lower():
                continue

            # check that this word is a known user (we have seen this username before)
            if not MassPingProtectionModule.is_known_user(matched_part):
                continue

            pings.add(matched_part)

        return len(pings)

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

        timeout_duration = self.determine_timeout_length(message, source, emote_instances)

        if timeout_duration <= 0:
            return

        self.bot.timeout_user(source, timeout_duration, reason="Too many users pinged in message")

        if self.settings["whisper_offenders"]:
            self.bot.whisper(
                source.username,
                (
                    "You have been timed out for {} seconds because your message mentioned too many users at once."
                ).format(timeout_duration),
            )

        return False

    def enable(self, bot):
        HandlerManager.add_handler("on_message", self.on_message, priority=150)

    def disable(self, bot):
        HandlerManager.remove_handler("on_message", self.on_message)

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
    def count_pings(message):
        potential_usernames = username_in_message_pattern.finditer(message)
        # get the matched string part...
        potential_usernames = (x.group(0) for x in potential_usernames)
        # to lowercase + filter out matches that are too long...
        potential_usernames = (x.lower() for x in potential_usernames if len(x) <= 25)
        real_usernames = (x for x in potential_usernames if MassPingProtectionModule.is_known_user(x))

        # count real users
        # set() is used so the same user is only counted once
        return sum(1 for x in set(real_usernames))

    def on_pubmsg(self, source, message, **rest):
        if source.level >= self.settings["bypass_level"] or source.moderator is True:
            return

        ping_count = MassPingProtectionModule.count_pings(message)
        pings_too_many = max(ping_count - self.settings["max_ping_count"], 0)

        if pings_too_many <= 0:
            return

        timeout_duration = (
            self.settings["timeout_length_base"] + self.settings["extra_timeout_length_per_ping"] * pings_too_many
        )

        self.bot.timeout(source.username, timeout_duration, reason="Too many users pinged in message")

        if self.settings["whisper_offenders"]:
            self.bot.whisper(
                source.username,
                (
                    "You have been timed out for {} seconds because your " + "message mentioned too many users at once."
                ).format(timeout_duration),
            )

        return False

    def enable(self, bot):
        HandlerManager.add_handler("on_pubmsg", self.on_pubmsg)

    def disable(self, bot):
        HandlerManager.remove_handler("on_pubmsg", self.on_pubmsg)

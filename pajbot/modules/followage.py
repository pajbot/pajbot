import logging

from pajbot import utils
from pajbot.managers.db import DBManager
from pajbot.models.command import Command
from pajbot.models.command import CommandExample
from pajbot.models.user import User
from pajbot.modules import BaseModule
from pajbot.modules import ModuleSetting
from pajbot.utils import time_since

log = logging.getLogger("pajbot")


class FollowAgeModule(BaseModule):

    ID = __name__.split(".")[-1]
    NAME = "Follow age"
    DESCRIPTION = f"Makes two commands available: {self.prefix}followage and {self.prefix}followsince"
    CATEGORY = "Feature"
    SETTINGS = [
        ModuleSetting(
            key="action_followage",
            label=f"MessageAction for {self.prefix}followage",
            type="options",
            required=True,
            default="say",
            options=["say", "whisper", "reply"],
        ),
        ModuleSetting(
            key="action_followsince",
            label=f"MessageAction for {self.prefix}followsince",
            type="options",
            required=True,
            default="say",
            options=["say", "whisper", "reply"],
        ),
        ModuleSetting(
            key="global_cd",
            label="Global cooldown (seconds)",
            type="number",
            required=True,
            placeholder="",
            default=4,
            constraints={"min_value": 0, "max_value": 120},
        ),
        ModuleSetting(
            key="user_cd",
            label="Per-user cooldown (seconds)",
            type="number",
            required=True,
            placeholder="",
            default=8,
            constraints={"min_value": 0, "max_value": 240},
        ),
    ]

    def load_commands(self, **options):
        # TODO: Have delay modifiable in settings

        self.commands["followage"] = Command.raw_command(
            self.follow_age,
            delay_all=self.settings["global_cd"],
            delay_user=self.settings["user_cd"],
            description="Check your or someone elses follow age for a channel",
            can_execute_with_whisper=True,
            examples=[
                CommandExample(
                    None,
                    "Check your own follow age",
                    chat=f"user:{self.prefix}followage\n"
                    "bot:pajlada, you have been following Karl_Kons for 4 months and 24 days",
                    description="Check how long you have been following the current streamer (Karl_Kons in this case)",
                ).parse(),
                CommandExample(
                    None,
                    "Check someone elses follow age",
                    chat=f"user:{self.prefix}followage NightNacht\n"
                    "bot:pajlada, NightNacht has been following Karl_Kons for 5 months and 4 days",
                    description="Check how long any user has been following the current streamer (Karl_Kons in this case)",
                ).parse(),
                CommandExample(
                    None,
                    "Check someones follow age for a certain streamer",
                    chat=f"user:{self.prefix}followage NightNacht forsenlol\n"
                    "bot:pajlada, NightNacht has been following forsenlol for 1 year and 4 months",
                    description="Check how long NightNacht has been following forsenlol",
                ).parse(),
                CommandExample(
                    None,
                    "Check your own follow age for a certain streamer",
                    chat=f"user:{self.prefix}followage pajlada forsenlol\n"
                    "bot:pajlada, you have been following forsenlol for 1 year and 3 months",
                    description="Check how long you have been following forsenlol",
                ).parse(),
            ],
        )

        self.commands["followsince"] = Command.raw_command(
            self.follow_since,
            delay_all=self.settings["global_cd"],
            delay_user=self.settings["user_cd"],
            description="Check from when you or someone else first followed a channel",
            can_execute_with_whisper=True,
            examples=[
                CommandExample(
                    None,
                    "Check your own follow since",
                    chat=f"user:{self.prefix}followsince\n"
                    "bot:pajlada, you have been following Karl_Kons since 04 March 2015, 07:02:01 UTC",
                    description="Check when you first followed the current streamer (Karl_Kons in this case)",
                ).parse(),
                CommandExample(
                    None,
                    "Check someone elses follow since",
                    chat=f"user:{self.prefix}followsince NightNacht\n"
                    "bot:pajlada, NightNacht has been following Karl_Kons since 03 July 2014, 04:12:42 UTC",
                    description="Check when NightNacht first followed the current streamer (Karl_Kons in this case)",
                ).parse(),
                CommandExample(
                    None,
                    "Check someone elses follow since for another streamer",
                    chat=f"user:{self.prefix}followsince NightNacht forsenlol\n"
                    "bot:pajlada, NightNacht has been following forsenlol since 13 June 2013, 13:10:51 UTC",
                    description="Check when NightNacht first followed the given streamer (forsenlol)",
                ).parse(),
                CommandExample(
                    None,
                    "Check your follow since for another streamer",
                    chat=f"user:{self.prefix}followsince pajlada forsenlol\n"
                    "bot:pajlada, you have been following forsenlol since 16 December 1990, 03:06:51 UTC",
                    description="Check when you first followed the given streamer (forsenlol)",
                ).parse(),
            ],
        )

    @staticmethod
    def _format_for_follow_age(follow_since):
        human_age = time_since(utils.now().timestamp() - follow_since.timestamp(), 0)
        return f"for {human_age}"

    @staticmethod
    def _format_for_follow_since(follow_since):
        human_age = follow_since.strftime("%d %B %Y, %X %Z")
        return f"since {human_age}"

    @staticmethod
    def _parse_message(message):
        from_input = None
        to_input = None
        if message is not None and len(message) > 0:
            message_split = message.split(" ")
            if len(message_split) >= 1:
                from_input = message_split[0]
            if len(message_split) >= 2:
                to_input = message_split[1]

        return from_input, to_input

    def _handle_command(self, bot, source, message, event, format_cb, message_method):
        from_input, to_input = self._parse_message(message)

        with DBManager.create_session_scope(expire_on_commit=False) as db_session:
            if from_input is not None:
                from_user = User.find_or_create_from_user_input(db_session, bot.twitch_helix_api, from_input)

                if from_user is None:
                    bot.execute_now(
                        bot.send_message_to_user,
                        source,
                        f'User "{from_input}" could not be found',
                        event,
                        method=self.settings["action_followage"],
                    )
                    return
            else:
                from_user = source

            if to_input is None:
                to_input = bot.streamer  # TODO make bot.streamer a User() instance?

            to_user = User.find_or_create_from_user_input(db_session, bot.twitch_helix_api, to_input)
            if to_user is None:
                bot.execute_now(
                    bot.send_message_to_user,
                    source,
                    f'User "{to_input}" could not be found',
                    event,
                    method=message_method,
                )
                return

        follow_since = bot.twitch_helix_api.get_follow_since(from_user.id, to_user.id)
        is_self = source == from_user

        if follow_since is not None:
            # Following
            suffix = f"been following {to_user} {format_cb(follow_since)}"
            if is_self:
                message = "You have " + suffix
            else:
                message = from_user.name + " has " + suffix
        else:
            # Not following
            suffix = f"not following {to_user}"
            if is_self:
                message = "You are " + suffix
            else:
                message = from_user.name + " is " + suffix

        bot.execute_now(bot.send_message_to_user, source, message, event, method=message_method)

    def follow_age(self, bot, source, message, event, **rest):
        self.bot.action_queue.submit(
            self._handle_command,
            bot,
            source,
            message,
            event,
            self._format_for_follow_age,
            self.settings["action_followage"],
        )

    def follow_since(self, bot, source, message, event, **rest):
        self.bot.action_queue.submit(
            self._handle_command,
            bot,
            source,
            message,
            event,
            self._format_for_follow_since,
            self.settings["action_followsince"],
        )

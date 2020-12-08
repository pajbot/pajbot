import logging
from datetime import timedelta

from pajbot.managers.handler import HandlerManager
from pajbot.managers.db import DBManager
from pajbot.modules import BaseModule
from pajbot.modules import ModuleSetting
from pajbot.models.user import User
from pajbot import utils

log = logging.getLogger(__name__)


class ChannelPointTimeout(BaseModule):
    ID = __name__.split(".")[-1]
    NAME = "Channel Point Timeout"
    DESCRIPTION = "Timeout people with channel points"
    CATEGORY = "Feature"
    SETTINGS = [
        ModuleSetting(
            key="redeemed_id_timeout",
            label="ID of redemeed prize for timeout",
            type="text",
            required=True,
            default="",
            constraints={"min_str_len": 36, "max_str_len": 36},
        ),
        ModuleSetting(
            key="redeemed_id_untimeout",
            label="ID of redemeed prize for untimeout",
            type="text",
            required=True,
            default="",
            constraints={"min_str_len": 36, "max_str_len": 36},
        ),
        ModuleSetting(key="timeout_duration", label="Duration in seconds for the timeout", type="number", required=True, default=3600),
        ModuleSetting(key="vip_immune", label="Are vips immune to timeouts?", type="boolean", required=True, default=True),
    ]

    def __init__(self, bot):
        super().__init__(bot)
        self.user_list = {}
        # {
        #     "user_id": timeout_expiry_date_time
        # }

    def on_redeem(self, redeemer, redeemed_id, user_input):
        if user_input is not None:
            username = user_input.split()[0]
            if redeemed_id not in [self.settings["redeemed_id_timeout"], self.settings["redeemed_id_untimeout"]]:
                return

            with DBManager.create_session_scope() as db_session:
                user = User.find_by_user_input(db_session, username)
                if not user:
                    self.bot.whisper(redeemer, f"{username} has never typed in the chat.")
                    return

                if user.level >= 500 or user.moderator:
                    self.bot.whisper(redeemer, "You cannout timeout moderators!")
                    return

                if user.vip and self.settings["vip_immune"]:
                    self.bot.whisper(redeemer, "You cannout vips!")
                    return

                str_user_id = str(user.id)
                if redeemed_id == self.settings["redeemed_id_timeout"]:
                    if user.timed_out:
                        self.bot.whisper(redeemer, "This user is already timedout!")
                        return

                    duration = self.settings["timeout_duration"]
                    self.user_list[str_user_id] = utils.now() + timedelta(seconds=duration)
                    self.bot.timeout(user, duration, f"{redeemer.name} paid for their timeout")
                    self.bot.whisper(redeemer, f"Timedout {user.name} for {duration} seconds")
                    if not user.ignored:
                        user.num_paid_timeouts += 1
                    return

                if str_user_id not in self.user_list or self.user_list[str_user_id] < utils.now():
                    self.bot.whisper(redeemer, "You can only untimeout people who have been timedout by this module.")
                    if str_user_id in self.user_list:
                        del self.user_list[str_user_id]
                    return

                self.bot.untimeout(user)
                user.timed_out = False
                self.bot.whisper(redeemer, f"Successfully untimed-out {user.name}")
                del self.user_list[str_user_id]

    def isReward(self, event):
        for eventTag in event.tags:
            if eventTag["key"] == "custom-reward-id":
                return eventTag["value"]

        return False

    def on_message(self, source, message, event, **rest):
        reward_id = self.isReward(event)
        if not reward_id:
            return

        self.on_redeem(source, reward_id, message)

    def enable(self, bot):
        if not bot:
            return

        HandlerManager.add_handler("on_message", self.on_message)

    def disable(self, bot):
        if not bot:
            return

        HandlerManager.remove_handler("on_message", self.on_message)

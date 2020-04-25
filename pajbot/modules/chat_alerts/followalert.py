import logging

from pajbot.managers.db import DBManager
from pajbot.managers.handler import HandlerManager
from pajbot.models.user import User, UserBasics
from pajbot.modules import BaseModule
from pajbot.modules import ModuleSetting
from pajbot.modules.chat_alerts import ChatAlertModule

log = logging.getLogger(__name__)


class FollowAlertModule(BaseModule):
    ID = __name__.split(".")[-1]
    NAME = "Follow Alert"
    DESCRIPTION = "Prints a message in chat/whispers when a user follows the channel"
    CATEGORY = "Feature"
    ENABLED_DEFAULT = True
    PARENT_MODULE = ChatAlertModule
    SETTINGS = [
        ModuleSetting(
            key="chat_message",
            label="Enable a chat message for someone who follows",
            type="boolean",
            required=True,
            default=True,
        ),
        ModuleSetting(
            key="new_follow",
            label="New follow chat message | Available arguments: {username}",
            type="text",
            required=True,
            placeholder="Thanks for following {username}! PogChamp",
            default="Thanks for following {username}! PogChamp",
            constraints={"min_str_len": 10, "max_str_len": 400},
        ),
        ModuleSetting(
            key="whisper_message",
            label="Enable a whisper message for someone who follows",
            type="boolean",
            required=True,
            default=False,
        ),
        ModuleSetting(
            key="whisper_after",
            label="Whisper the message after X seconds",
            type="number",
            required=True,
            placeholder="",
            default=5,
            constraints={"min_value": 1, "max_value": 120},
        ),
        ModuleSetting(
            key="new_follow_whisper",
            label="Whisper message for new followers | Available arguments: {username}",
            type="text",
            required=True,
            placeholder="Thank you for following {username} <3",
            default="Thank you for following {username} <3",
            constraints={"min_str_len": 10, "max_str_len": 400},
        ),
        ModuleSetting(
            key="grant_points_on_follow",
            label="Give points to user when they follow. 0 = off",
            type="number",
            required=True,
            placeholder="",
            default=0,
            constraints={"min_value": 0, "max_value": 50000},
        ),
    ]

    def __init__(self, bot):
        super().__init__(bot)

    def on_follow(self, user):
        if self.settings["grant_points_on_follow"] <= 0:
            return

        user.points += self.settings["grant_points_on_follow"]
        self.bot.say(f"{user} was given {self.settings['grant_points_on_follow']} points for following! FeelsAmazingMan")

    def on_follow(self, user):
        """
        A new user just followed.
        Send the event to the websocket manager, and send a customized message in chat.
        """

        self.on_sub_shared(user)

        self.bot.kvi["active_subs"].inc()

        payload = {"username": user.name, "gifted_by": gifted_by}
        self.bot.websocket_manager.emit("new_sub", payload)

        if self.settings["chat_message"] is True:
            if sub_type == "Prime":
                self.bot.say(self.get_phrase("new_prime_sub", **payload))
            else:
                if gifted_by:
                    self.bot.say(self.get_phrase("new_gift_sub", **payload))
                else:
                    self.bot.say(self.get_phrase("new_sub", **payload))

        if self.settings["whisper_message"] is True:
            self.bot.execute_delayed(
                self.settings["whisper_after"], self.bot.whisper, user, self.get_phrase("new_sub_whisper", **payload)
            )

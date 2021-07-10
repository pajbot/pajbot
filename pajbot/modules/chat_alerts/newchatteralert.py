import logging

from pajbot.managers.handler import HandlerManager
from pajbot.modules import BaseModule
from pajbot.modules import ModuleSetting
from pajbot.modules.chat_alerts import ChatAlertModule

log = logging.getLogger(__name__)


class NewChatterAlertModule(BaseModule):
    ID = __name__.split(".")[-1]
    NAME = "New Chatter Alert"
    DESCRIPTION = "Prints a message in chat/whispers when a user announces they are new"
    CATEGORY = "Feature"
    ENABLED_DEFAULT = False
    PARENT_MODULE = ChatAlertModule
    SETTINGS = [
        ModuleSetting(
            key="chat_message",
            label="Enable a chat message for someone who announces they are new",
            type="boolean",
            required=True,
            default=True,
        ),
        ModuleSetting(
            key="new_chatter_message",
            label="New chatter chat message | Available arguments: {username}",
            type="text",
            required=True,
            placeholder="HeyGuys {username}, thanks for joining the stream!",
            default="HeyGuys {username}, thanks for joining the stream!",
            constraints={"min_str_len": 10, "max_str_len": 400},
        ),
        ModuleSetting(
            key="whisper_message",
            label="Enable a whisper message for a new chatter",
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
            key="new_chatter_whisper",
            label="Whisper message for new chatters | Available arguments: {username}",
            type="text",
            required=True,
            placeholder="HeyGuys {username}, thanks for joining the stream!",
            default="HeyGuys {username}, thanks for joining the stream!",
            constraints={"min_str_len": 10, "max_str_len": 400},
        ),
        ModuleSetting(
            key="grant_points_on_new_chatter",
            label="Give points to user when they announce they are a new chatter. 0 = off",
            type="number",
            required=True,
            placeholder="",
            default=0,
            constraints={"min_value": 0, "max_value": 1000000},
        ),
        ModuleSetting(
            key="alert_message_points_given",
            label="Message to announce points were given to user, leave empty to disable message. | Available arguments: {user}, {points}",
            type="text",
            required=True,
            default="{user} was given {points} points for being a new chatter! FeelsAmazingMan",
            constraints={"min_str_len": 0, "max_str_len": 300},
        ),
    ]

    def __init__(self, bot):
        super().__init__(bot)

    def on_new_chatter(self, user):
        """
        A user just announced they are a new chatter.
        Send the event to the websocket manager and send a customized message in chat/whispers.
        """

        payload = {"username": user.name}
        self.bot.websocket_manager.emit("new_chatter", payload)

        if self.settings["chat_message"] is True:
            self.bot.say(self.get_phrase("new_chatter_message", **payload))

        if self.settings["whisper_message"] is True:
            self.bot.execute_delayed(
                self.settings["whisper_after"],
                self.bot.whisper,
                user,
                self.get_phrase("new_chatter_whisper", **payload),
            )
        if self.settings["grant_points_on_new_chatter"] <= 0:
            return

        user.points += self.settings["grant_points_on_new_chatter"]

        alert_message = self.settings["alert_message_points_given"]
        if alert_message != "":
            self.bot.say(alert_message.format(user=user, points=self.settings["grant_points_on_new_chatter"]))

    def on_usernotice(self, source, tags, **rest):
        if "msg-id" not in tags:
            return

        if tags["msg-id"] == "ritual":
            if "display-name" not in tags:
                log.debug(f"newchatteralert requires a display-name, but it is missing: {tags}")
                return
            self.on_new_chatter(source)

    def enable(self, bot):
        HandlerManager.add_handler("on_usernotice", self.on_usernotice)

    def disable(self, bot):
        HandlerManager.remove_handler("on_usernotice", self.on_usernotice)

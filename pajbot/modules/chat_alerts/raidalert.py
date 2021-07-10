import logging

from pajbot.managers.handler import HandlerManager
from pajbot.modules import BaseModule
from pajbot.modules import ModuleSetting
from pajbot.modules.chat_alerts import ChatAlertModule

log = logging.getLogger(__name__)


class RaidAlertModule(BaseModule):
    ID = __name__.split(".")[-1]
    NAME = "Raid Alert"
    DESCRIPTION = "Prints a message in chat/whispers when a user raids your channel"
    CATEGORY = "Feature"
    ENABLED_DEFAULT = False
    PARENT_MODULE = ChatAlertModule
    SETTINGS = [
        ModuleSetting(
            key="chat_message",
            label="Enable a chat message for someone who raids",
            type="boolean",
            required=True,
            default=True,
        ),
        ModuleSetting(
            key="new_raid",
            label="Raid chat message | Available arguments: {username}, {num_viewers}",
            type="text",
            required=True,
            placeholder="{username} just raided the channel with {num_viewers} viewers PogChamp",
            default="{username} just raided the channel with {num_viewers} viewers PogChamp",
            constraints={"min_str_len": 10, "max_str_len": 400},
        ),
        ModuleSetting(
            key="whisper_message",
            label="Enable a whisper message for someone who raids",
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
            key="raid_whisper",
            label="Whisper message for raids | Available arguments: {username}, {num_viewers}",
            type="text",
            required=True,
            placeholder="Thank you for raiding with {num_viewers} viewers {username} <3",
            default="Thank you for raiding with {num_viewers} viewers {username} <3",
            constraints={"min_str_len": 10, "max_str_len": 400},
        ),
        ModuleSetting(
            key="multiply_points_by_raiders",
            label="Multiply the number of points specified by the number of raiders",
            type="boolean",
            required=True,
            default=False,
        ),
        ModuleSetting(
            key="grant_points_on_raid",
            label="Give points to user when they raid. 0 = off",
            type="number",
            required=True,
            placeholder="",
            default=0,
            constraints={"min_value": 0, "max_value": 1000000},
        ),
        ModuleSetting(
            key="min_viewers",
            label="Minimum amount of viewers required to trigger the alert. 0 = all raids",
            type="number",
            required=True,
            placeholder="",
            default=0,
            constraints={"min_value": 0},
        ),
        ModuleSetting(
            key="alert_message_points_given",
            label="Message to announce points were given to user, leave empty to disable message. | Available arguments: {user}, {points}",
            type="text",
            required=True,
            default="{user} was given {points} points for raiding the channel! FeelsAmazingMan",
            constraints={"min_str_len": 0, "max_str_len": 300},
        ),
    ]

    def __init__(self, bot):
        super().__init__(bot)

    def on_raid(self, user, num_viewers):
        """
        A new user just raided.
        Send the event to the websocket manager, and send a customized message in chat.
        """

        payload = {"username": user.name, "num_viewers": num_viewers}
        self.bot.websocket_manager.emit("new_raid", payload)

        if num_viewers < self.settings["min_viewers"]:
            return

        if self.settings["chat_message"] is True:
            self.bot.say(self.get_phrase("new_raid", **payload))

        if self.settings["whisper_message"] is True:
            self.bot.execute_delayed(
                self.settings["whisper_after"], self.bot.whisper, user, self.get_phrase("raid_whisper", **payload)
            )
        if self.settings["grant_points_on_raid"] <= 0:
            return

        awarded_points = self.settings["grant_points_on_raid"]
        if self.settings["multiply_points_by_raiders"] is True:
            awarded_points *= num_viewers

        user.points += awarded_points

        alert_message = self.settings["alert_message_points_given"]
        if alert_message != "":
            self.bot.say(alert_message.format(user=user, points=awarded_points))

    def on_usernotice(self, source, tags, **rest):
        if "msg-id" not in tags:
            return

        if tags["msg-id"] == "raid":
            if "msg-param-viewerCount" in tags:
                num_viewers = int(tags["msg-param-viewerCount"])
            else:
                log.debug(f"raidalert requires viewerCount, but it is missing: {tags}")
                return

            if "display-name" not in tags:
                log.debug(f"raidalert requires a display-name, but it is missing: {tags}")
                return
            self.on_raid(source, num_viewers)

    def enable(self, bot):
        HandlerManager.add_handler("on_usernotice", self.on_usernotice)

    def disable(self, bot):
        HandlerManager.remove_handler("on_usernotice", self.on_usernotice)

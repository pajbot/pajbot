import logging
import math

from pajbot.managers.handler import HandlerManager
from pajbot.modules import BaseModule
from pajbot.modules import ModuleSetting
from pajbot.modules.chat_alerts import ChatAlertModule

log = logging.getLogger(__name__)


class CheerAlertModule(BaseModule):
    ID = __name__.split(".")[-1]
    NAME = "Cheer Alert"
    DESCRIPTION = "Prints a message in chat/whispers when a user cheers in your chat"
    CATEGORY = "Feature"
    ENABLED_DEFAULT = False
    PARENT_MODULE = ChatAlertModule
    SETTINGS = [
        ModuleSetting(
            key="chat_message",
            label="Enable chat messages for users who cheer bits",
            type="boolean",
            required=True,
            default=True,
        ),
        ModuleSetting(
            key="whisper_message",
            label="Enable whisper messages for users who cheer bits",
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
            key="1_bit",
            label="Chat message for users who cheer 1 or more bits | Available arguments: {username}, {num_bits}",
            type="text",
            required=True,
            placeholder="{username} thank you so much for cheering {num_bits} bits! PogChamp",
            default="{username} thank you so much for cheering {num_bits} bits! PogChamp",
            constraints={"min_str_len": 10, "max_str_len": 400},
        ),
        ModuleSetting(
            key="69_bits",
            label="Chat message for users who cheer 69 bits, leave empty to fallback to the previous bit amount message. | Available arguments: {username}, {num_bits}",
            type="text",
            required=True,
            placeholder="{username} thank you so much for cheering {num_bits} bits! Kreygasm",
            default="",
            constraints={"min_str_len": 10, "max_str_len": 400},
        ),
        ModuleSetting(
            key="100_bits",
            label="Chat message for users who cheer 100 or more bits, leave empty to fallback to the previous bit amount message. | Available arguments: {username}, {num_bits}",
            type="text",
            required=True,
            placeholder="{username} thank you so much for cheering {num_bits} bits! PogChamp",
            default="",
            constraints={"min_str_len": 10, "max_str_len": 400},
        ),
        ModuleSetting(
            key="420_bits",
            label="Chat message for users who cheer 420 bits, leave empty to fallback to the previous bit amount message. | Available arguments: {username}, {num_bits}",
            type="text",
            required=True,
            placeholder="{username} thank you so much for cheering {num_bits} bits! CiGrip",
            default="",
            constraints={"min_str_len": 10, "max_str_len": 400},
        ),
        ModuleSetting(
            key="500_bits",
            label="Chat message for users who cheer 500 or more bits, leave empty to fallback to the previous bit amount message. | Available arguments: {username}, {num_bits}",
            type="text",
            required=True,
            placeholder="{username} thank you so much for cheering {num_bits} bits! PogChamp",
            default="",
            constraints={"min_str_len": 10, "max_str_len": 400},
        ),
        ModuleSetting(
            key="1500_bits",
            label="Chat message for users who cheer 1500 or more bits, leave empty to fallback to the previous bit amount message. | Available arguments: {username}, {num_bits}",
            type="text",
            required=True,
            placeholder="{username} thank you so much for cheering {num_bits} bits! PogChamp",
            default="",
            constraints={"min_str_len": 10, "max_str_len": 400},
        ),
        ModuleSetting(
            key="5000_bits",
            label="Chat message for users who cheer 5000 or more bits, leave empty to fallback to the previous bit amount message. | Available arguments: {username}, {num_bits}",
            type="text",
            required=True,
            placeholder="{username} thank you so much for cheering {num_bits} bits! PogChamp",
            default="",
            constraints={"min_str_len": 10, "max_str_len": 400},
        ),
        ModuleSetting(
            key="10000_bits",
            label="Chat message for users who cheer 10000 or more bits, leave empty to fallback to the previous bit amount message. | Available arguments: {username}, {num_bits}",
            type="text",
            required=True,
            placeholder="{username} thank you so much for cheering {num_bits} bits! PogChamp",
            default="",
            constraints={"min_str_len": 10, "max_str_len": 400},
        ),
        ModuleSetting(
            key="25000_bits",
            label="Chat message for users who cheer 25000 or more bits, leave empty to fallback to the previous bit amount message. | Available arguments: {username}, {num_bits}",
            type="text",
            required=True,
            placeholder="{username} thank you so much for cheering {num_bits} bits! PogChamp",
            default="",
            constraints={"min_str_len": 10, "max_str_len": 400},
        ),
        ModuleSetting(
            key="grant_points_per_100_bits",
            label="Give points to user per 100 bits they cheer. 0 = off",
            type="number",
            required=True,
            placeholder="",
            default=0,
            constraints={"min_value": 0, "max_value": 50000},
        ),
        ModuleSetting(
            key="alert_message_points_given",
            label="Message to announce points were given to user, leave empty to disable message. | Available arguments: {user}, {points}, {num_bits}",
            type="text",
            required=True,
            default="{username} was given {points} points for cheering {num_bits}! FeelsAmazingMan",
            constraints={"min_str_len": 0, "max_str_len": 300},
        ),
    ]

    def __init__(self, bot):
        super().__init__(bot)

    def on_cheer(self, user, num_bits):
        """
        A user just cheered bits.
        Send the event to the websocket manager, and send a customized message in chat.
        """

        payload = {"username": user.name, "num_bits": num_bits}
        self.bot.websocket_manager.emit("cheer", payload)

        if self.settings["chat_message"]:
            if num_bits >= 25000 and self.settings["25000_bits"] != "":
                self.bot.say(self.get_phrase("25000_bits", **payload))
            elif num_bits >= 10000 and self.settings["10000_bits"] != "":
                self.bot.say(self.get_phrase("10000_bits", **payload))
            elif num_bits >= 5000 and self.settings["5000_bits"] != "":
                self.bot.say(self.get_phrase("5000_bits", **payload))
            elif num_bits >= 1500 and self.settings["1500_bits"] != "":
                self.bot.say(self.get_phrase("1500_bits", **payload))
            elif num_bits >= 500 and self.settings["500_bits"] != "":
                self.bot.say(self.get_phrase("500_bits", **payload))
            elif num_bits == 420 and self.settings["420_bits"] != "":
                self.bot.say(self.get_phrase("420_bits", **payload))
            elif num_bits >= 100 and self.settings["100_bits"] != "":
                self.bot.say(self.get_phrase("100_bits", **payload))
            elif num_bits == 69 and self.settings["69_bits"] != "":
                self.bot.say(self.get_phrase("69_bits", **payload))
            elif self.settings["1_bit"] != "":
                self.bot.say(self.get_phrase("1_bit", **payload))
            else:
                log.warning("Something went wrong with the bit amount announcement!!!!")

        if self.settings["whisper_message"]:
            if num_bits >= 25000 and self.settings["25000_bits"] != "":
                self.bot.execute_delayed(
                    self.settings["whisper_after"],
                    self.bot.whisper,
                    user,
                    self.get_phrase("25000_bits", **payload),
                )
            elif num_bits >= 10000 and self.settings["10000_bits"] != "":
                self.bot.execute_delayed(
                    self.settings["whisper_after"],
                    self.bot.whisper,
                    user,
                    self.get_phrase("10000_bits", **payload),
                )
            elif num_bits >= 5000 and self.settings["5000_bits"] != "":
                self.bot.execute_delayed(
                    self.settings["whisper_after"],
                    self.bot.whisper,
                    user,
                    self.get_phrase("5000_bits", **payload),
                )
            elif num_bits >= 1500 and self.settings["1500_bits"] != "":
                self.bot.execute_delayed(
                    self.settings["whisper_after"],
                    self.bot.whisper,
                    user,
                    self.get_phrase("1500_bits", **payload),
                )
            elif num_bits >= 500 and self.settings["500_bits"] != "":
                self.bot.execute_delayed(
                    self.settings["whisper_after"],
                    self.bot.whisper,
                    user,
                    self.get_phrase("500_bits", **payload),
                )
            elif num_bits == 420 and self.settings["420_bits"] != "":
                self.bot.execute_delayed(
                    self.settings["whisper_after"],
                    self.bot.whisper,
                    user,
                    self.get_phrase("420_bits", **payload),
                )
            elif num_bits >= 100 and self.settings["100_bits"] != "":
                self.bot.execute_delayed(
                    self.settings["whisper_after"],
                    self.bot.whisper,
                    user,
                    self.get_phrase("100_bits", **payload),
                )
            elif num_bits == 69 and self.settings["69_bits"] != "":
                self.bot.execute_delayed(
                    self.settings["whisper_after"],
                    self.bot.whisper,
                    user,
                    self.get_phrase("69_bits", **payload),
                )
            elif self.settings["1_bit"] != "":
                self.bot.execute_delayed(
                    self.settings["whisper_after"],
                    self.bot.whisper,
                    user,
                    self.get_phrase("1_bit", **payload),
                )
            else:
                log.warning("Something went wrong with the bit amount announcement!!!!")

        if self.settings["grant_points_per_100_bits"] <= 0:
            return

        round_number = math.floor(num_bits / 100)

        if round_number > 0:
            points_to_grant = round_number * self.settings["grant_points_per_100_bits"]
        else:
            return

        user.points += points_to_grant
        alert_message = self.settings["alert_message_points_given"]
        if alert_message != "":
            self.bot.say(alert_message.format(user=user, points=points_to_grant, num_bits=num_bits))

    def on_pubmsg(self, source, tags, **rest):
        if "bits" not in tags:
            return

        if tags["bits"] != 0:
            num_bits = int(tags["bits"])
        else:
            log.debug("cheeralert required bits to equal more than 0, but it is equal to 0")
            return

        if "display-name" not in tags:
            log.debug(f"raidalert requires a display-name, but it is missing: {tags}")
            return
        self.on_cheer(source, num_bits)

    def enable(self, bot):
        HandlerManager.add_handler("on_pubmsg", self.on_pubmsg)

    def disable(self, bot):
        HandlerManager.remove_handler("on_pubmsg", self.on_pubmsg)

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

import logging
import math

from pajbot.managers.handler import HandlerManager, HandlerResponse, ResponseMeta
from pajbot.message_event import MessageEvent
from pajbot.models.emote import EmoteInstance, EmoteInstanceCountMap
from pajbot.models.user import User
from pajbot.modules import BaseModule, ModuleSetting
from pajbot.modules.chat_alerts import ChatAlertModule

if TYPE_CHECKING:
    from pajbot.bot import Bot

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
            key="one_bit",
            label="Chat message for users who cheer 1 or more bits | Available arguments: {username}, {num_bits}",
            type="text",
            required=True,
            placeholder="{username} thank you so much for cheering {num_bits} bits! PogChamp",
            default="{username} thank you so much for cheering {num_bits} bits! PogChamp",
            constraints={"max_str_len": 400},
        ),
        ModuleSetting(
            key="sixnine_bits",
            label="Chat message for users who cheer 69 bits, leave empty to fallback to the previous bit amount message. | Available arguments: {username}, {num_bits}",
            type="text",
            required=True,
            placeholder="{username} thank you so much for cheering {num_bits} bits! Kreygasm",
            default="",
            constraints={"max_str_len": 400},
        ),
        ModuleSetting(
            key="hundred_bits",
            label="Chat message for users who cheer 100 or more bits, leave empty to fallback to the previous bit amount message. | Available arguments: {username}, {num_bits}",
            type="text",
            required=True,
            placeholder="{username} thank you so much for cheering {num_bits} bits! PogChamp",
            default="",
            constraints={"max_str_len": 400},
        ),
        ModuleSetting(
            key="fourtwenty_bits",
            label="Chat message for users who cheer 420 bits, leave empty to fallback to the previous bit amount message. | Available arguments: {username}, {num_bits}",
            type="text",
            required=True,
            placeholder="{username} thank you so much for cheering {num_bits} bits! CiGrip",
            default="",
            constraints={"max_str_len": 400},
        ),
        ModuleSetting(
            key="fivehundred_bits",
            label="Chat message for users who cheer 500 or more bits, leave empty to fallback to the previous bit amount message. | Available arguments: {username}, {num_bits}",
            type="text",
            required=True,
            placeholder="{username} thank you so much for cheering {num_bits} bits! PogChamp",
            default="",
            constraints={"max_str_len": 400},
        ),
        ModuleSetting(
            key="fifteenhundred_bits",
            label="Chat message for users who cheer 1500 or more bits, leave empty to fallback to the previous bit amount message. | Available arguments: {username}, {num_bits}",
            type="text",
            required=True,
            placeholder="{username} thank you so much for cheering {num_bits} bits! PogChamp",
            default="",
            constraints={"max_str_len": 400},
        ),
        ModuleSetting(
            key="fivethousand_bits",
            label="Chat message for users who cheer 5000 or more bits, leave empty to fallback to the previous bit amount message. | Available arguments: {username}, {num_bits}",
            type="text",
            required=True,
            placeholder="{username} thank you so much for cheering {num_bits} bits! PogChamp",
            default="",
            constraints={"max_str_len": 400},
        ),
        ModuleSetting(
            key="tenthousand_bits",
            label="Chat message for users who cheer 10000 or more bits, leave empty to fallback to the previous bit amount message. | Available arguments: {username}, {num_bits}",
            type="text",
            required=True,
            placeholder="{username} thank you so much for cheering {num_bits} bits! PogChamp",
            default="",
            constraints={"max_str_len": 400},
        ),
        ModuleSetting(
            key="twentyfivethousand_bits",
            label="Chat message for users who cheer 25000 or more bits, leave empty to fallback to the previous bit amount message. | Available arguments: {username}, {num_bits}",
            type="text",
            required=True,
            placeholder="{username} thank you so much for cheering {num_bits} bits! PogChamp",
            default="",
            constraints={"max_str_len": 400},
        ),
        ModuleSetting(
            key="grant_points_per_100_bits",
            label="Give points to user per 100 bits they cheer. 0 = off",
            type="number",
            required=True,
            placeholder="",
            default=0,
            constraints={"min_value": 0, "max_value": 1000000},
        ),
        ModuleSetting(
            key="alert_message_points_given",
            label="Message to announce points were given to user, leave empty to disable message. If the user cheers less than 100 bits, no message will be sent. | Available arguments: {username}, {points}, {num_bits}",
            type="text",
            required=True,
            default="{username} was given {points} points for cheering {num_bits} bits! FeelsAmazingMan",
            constraints={"max_str_len": 300},
        ),
    ]

    def __init__(self, bot: Optional[Bot]) -> None:
        super().__init__(bot)

    def on_cheer(self, user: User, num_bits: int) -> HandlerResponse:
        """
        A user just cheered bits.
        Send the event to the websocket manager, and send a customized message in chat.
        """

        assert self.bot is not None

        payload = {"username": user.name, "num_bits": num_bits}
        self.bot.websocket_manager.emit("cheer", payload)

        res = HandlerResponse()

        if self.settings["chat_message"]:
            if num_bits >= 25000 and self.settings["twentyfivethousand_bits"] != "":
                res.say(self.get_phrase("twentyfivethousand_bits", **payload))
            elif num_bits >= 10000 and self.settings["tenthousand_bits"] != "":
                res.say(self.get_phrase("tenthousand_bits", **payload))
            elif num_bits >= 5000 and self.settings["fivethousand_bits"] != "":
                res.say(self.get_phrase("fivethousand_bits", **payload))
            elif num_bits >= 1500 and self.settings["fifteenhundred_bits"] != "":
                res.say(self.get_phrase("fifteenhundred_bits", **payload))
            elif num_bits >= 500 and self.settings["fivehundred_bits"] != "":
                res.say(self.get_phrase("fivehundred_bits", **payload))
            elif num_bits == 420 and self.settings["fourtwenty_bits"] != "":
                res.say(self.get_phrase("fourtwenty_bits", **payload))
            elif num_bits >= 100 and self.settings["hundred_bits"] != "":
                res.say(self.get_phrase("hundred_bits", **payload))
            elif num_bits == 69 and self.settings["sixnine_bits"] != "":
                res.say(self.get_phrase("sixnine_bits", **payload))
            elif self.settings["one_bit"] != "":
                res.say(self.get_phrase("one_bit", **payload))

        if self.settings["whisper_message"]:
            if num_bits >= 25000 and self.settings["twentyfivethousand_bits"] != "":
                res.whisper(
                    user.id,
                    self.get_phrase("twentyfivethousand_bits", **payload),
                    self.settings["whisper_after"],
                )
            elif num_bits >= 10000 and self.settings["tenthousand_bits"] != "":
                res.whisper(
                    user.id,
                    self.get_phrase("tenthousand_bits", **payload),
                    self.settings["whisper_after"],
                )
            elif num_bits >= 5000 and self.settings["fivethousand_bits"] != "":
                res.whisper(
                    user.id,
                    self.get_phrase("fivethousand_bits", **payload),
                    self.settings["whisper_after"],
                )
            elif num_bits >= 1500 and self.settings["fifteenhundred_bits"] != "":
                res.whisper(
                    user.id,
                    self.get_phrase("fifteenhundred_bits", **payload),
                    self.settings["whisper_after"],
                )
            elif num_bits >= 500 and self.settings["fivehundred_bits"] != "":
                res.whisper(
                    user.id,
                    self.get_phrase("fivehundred_bits", **payload),
                    self.settings["whisper_after"],
                )
            elif num_bits == 420 and self.settings["fourtwenty_bits"] != "":
                res.whisper(
                    user.id,
                    self.get_phrase("fourtwenty_bits", **payload),
                    self.settings["whisper_after"],
                )
            elif num_bits >= 100 and self.settings["hundred_bits"] != "":
                res.whisper(
                    user.id,
                    self.get_phrase("hundred_bits", **payload),
                    self.settings["whisper_after"],
                )
            elif num_bits == 69 and self.settings["sixnine_bits"] != "":
                res.whisper(
                    user.id,
                    self.get_phrase("sixnine_bits", **payload),
                    self.settings["whisper_after"],
                )
            elif self.settings["one_bit"] != "":
                res.whisper(
                    user.id,
                    self.get_phrase("one_bit", **payload),
                    self.settings["whisper_after"],
                )

        if self.settings["grant_points_per_100_bits"] > 0:
            round_number = math.floor(num_bits / 100)

            if round_number > 0:
                points_to_grant = round_number * self.settings["grant_points_per_100_bits"]
                user.points += points_to_grant
                alert_message = self.settings["alert_message_points_given"]
                if alert_message != "":
                    res.say(alert_message.format(username=user, points=points_to_grant, num_bits=num_bits))

        return res

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
        if event.num_bits_spent <= 0:
            return HandlerResponse.null()

        return self.on_cheer(source, event.num_bits_spent)

    def enable(self, bot: Bot | None) -> None:
        if bot:
            HandlerManager.register_on_message(self.on_message)

    def disable(self, bot: Bot | None) -> None:
        if bot:
            HandlerManager.unregister_on_message(self.on_message)

import logging
import re

from unidecode import unidecode

from pajbot.managers.handler import HandlerManager
from pajbot.modules import BaseModule
from pajbot.modules import ModuleSetting

log = logging.getLogger(__name__)


class PyramidModule(BaseModule):

    ID = __name__.split(".")[-1]
    NAME = "Pyramid"
    DESCRIPTION = "Congratulates people who build successfully pyramids in twitch chat"
    CATEGORY = "Game"
    SETTINGS = [
        ModuleSetting(
            key="message_5",
            label="Message for a < 5 pyramid | Available arguments: {user}, {width}, {emote}",
            type="text",
            required=True,
            placeholder=".me {user} just finished a {width}-width {emote} pyramid! That's pretty neat KKona //",
            default=".me {user} just finished a {width}-width {emote} pyramid! That's pretty neat KKona //",
            constraints={"min_str_len": 10, "max_str_len": 400},
        ),
        ModuleSetting(
            key="message_7",
            label="Message for a < 7 pyramid | Available arguments: {user}, {width}, {emote}",
            type="text",
            required=True,
            placeholder=".me {user} just finished a {width}-width {emote} pyramid! Good job!!! PogChamp //",
            default=".me {user} just finished a {width}-width {emote} pyramid! Good job!!! PogChamp //",
            constraints={"min_str_len": 10, "max_str_len": 400},
        ),
        ModuleSetting(
            key="message_15",
            label="Message for a < 15 pyramid | Available arguments: {user}, {width}, {emote}",
            type="text",
            required=True,
            placeholder=".me {user} just finished a {width}-width {emote} pyramid! Now that's what I call pyramid-farming Kappa // PogChamp //",
            default=".me {user} just finished a {width}-width {emote} pyramid! Now that's what I call pyramid-farming Kappa // PogChamp //",
            constraints={"min_str_len": 10, "max_str_len": 400},
        ),
        ModuleSetting(
            key="message_25",
            label="Message for a < 25 pyramid | Available arguments: {user}, {width}, {emote}",
            type="text",
            required=True,
            placeholder=".me {user} just finished a {width}-width {emote} pyramid! Wow, I can't even fit this pyramid in my memory bank MrDestructoid //",
            default=".me {user} just finished a {width}-width {emote} pyramid! Wow, I can't even fit this pyramid in my memory bank MrDestructoid //",
            constraints={"min_str_len": 10, "max_str_len": 400},
        ),
        ModuleSetting(
            key="message_else",
            label="Message for a >= 25 pyramid | Available arguments: {user}, {width}, {emote}",
            type="text",
            required=True,
            placeholder=".me {user} just finished a {width}-width {emote} pyramid! BUFFER OVERFLOW WutFace //",
            default=".me {user} just finished a {width}-width {emote} pyramid! BUFFER OVERFLOW WutFace //",
            constraints={"min_str_len": 10, "max_str_len": 400},
        ),
    ]

    def __init__(self, bot):
        super().__init__(bot)
        self.data = []
        self.going_down = False
        self.regex = re.compile(" +")

    def on_pubmsg(self, source, message, **rest):
        if source.username == "twitchnotify":
            return

        # remove the invisible Chatterino suffix
        message = unidecode(message).strip()

        try:
            msg_parts = message.split(" ")
            if len(self.data) > 0:
                cur_len = len(msg_parts)
                last_len = len(self.data[-1])
                pyramid_thing = self.data[-1][0]
                len_diff = cur_len - last_len
                if abs(len_diff) == 1:
                    good = True

                    # Make sure the pyramid consists of the same item over and over again
                    for x in msg_parts:
                        if not x == pyramid_thing:
                            good = False
                            break

                    if good:
                        self.data.append(msg_parts)
                        if len_diff > 0:
                            if self.going_down:
                                self.data = []
                                self.going_down = False
                        elif len_diff < 0:
                            self.going_down = True
                            if cur_len == 1:
                                # A pyramid was finished
                                peak_length = 0
                                for x in self.data:
                                    if len(x) > peak_length:
                                        peak_length = len(x)

                                arguments = {"emote": pyramid_thing, "user": source.username_raw, "width": peak_length}

                                if peak_length > 2:
                                    if peak_length < 5:
                                        self.bot.say(self.get_phrase("message_5", **arguments))
                                    elif peak_length < 7:
                                        self.bot.say(self.get_phrase("message_7", **arguments))
                                    elif peak_length < 15:
                                        self.bot.say(self.get_phrase("message_15", **arguments))
                                    elif peak_length < 25:
                                        self.bot.say(self.get_phrase("message_25", **arguments))
                                    else:
                                        self.bot.say(self.get_phrase("message_else", **arguments))
                                self.data = []
                                self.going_down = False
                    else:
                        self.data = []
                        self.going_down = False
                else:
                    self.data = []
                    self.going_down = False

            if len(msg_parts) == 1 and len(self.data) == 0:
                self.data.append(msg_parts)
        except:
            # Let's just catch all exceptions, in case I fucked up in the above spaghetti code
            log.exception("Unhandled exception in pyramid parser")

    def enable(self, bot):
        HandlerManager.add_handler("on_pubmsg", self.on_pubmsg)

    def disable(self, bot):
        HandlerManager.remove_handler("on_pubmsg", self.on_pubmsg)

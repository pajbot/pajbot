import logging
from functools import reduce

from numpy import random

from pajbot.managers.handler import HandlerManager
from pajbot.models.command import Command
from pajbot.models.command import CommandExample
from pajbot.modules import BaseModule
from pajbot.modules import ModuleSetting

log = logging.getLogger(__name__)


class BingoGame:
    def __init__(self, correct_emote, points_reward):
        self.correct_emote = correct_emote
        self.points_reward = points_reward


class BingoModule(BaseModule):
    ID = __name__.split(".")[-1]
    NAME = "Bingo Games"
    DESCRIPTION = "Chat Bingo Game for Twitch, FFZ and BTTV Emotes"
    ENABLED_DEFAULT = False
    CATEGORY = "Game"
    SETTINGS = [
        ModuleSetting(
            key="max_points",
            label="Max points for a bingo",
            type="number",
            required=True,
            placeholder="",
            default=3000,
            constraints={"min_value": 0, "max_value": 35000},
        ),
        ModuleSetting(
            key="allow_negative_bingo", label="Allow negative bingo", type="boolean", required=True, default=True
        ),
        ModuleSetting(
            key="max_negative_points",
            label="Max negative points for a bingo",
            type="number",
            required=True,
            placeholder="",
            default=1500,
            constraints={"min_value": 1, "max_value": 35000},
        ),
    ]

    def __init__(self, bot):
        super().__init__(bot)
        self.active_game = None

    def begin_game(self, correct_emote, points_reward):
        self.active_game = BingoGame(correct_emote, points_reward)

    @property
    def bingo_running(self):
        return self.active_game is not None

    def bingo_start(self, bot, source, message, event, args):
        pass

    def bingo_cancel(self, bot, source, message, event, args):
        pass

    def bingo_help_random(self, bot, source, message, event, args):
        pass

    def bingo_help_first(self, bot, source, message, event, args):
        pass

    def on_message(self, source, message, emote_instances, **rest):
        pass

    def load_commands(self, **options):
        self.commands["bingo"] = Command.multiaction_command(
            level=500,
            default=None,
            command="bingo",
            commands={
                "start": Command.raw_command(
                    self.bingo_start,
                    level=500,
                    delay_all=15,
                    delay_user=15,
                    description="Start an emote bingo with specified emote sets",
                    examples=[
                        CommandExample(
                            None,
                            "Emote bingo for 100 points",
                            chat="user:!bingo emotes\n"
                            "bot: A bingo has started! Guess the right target to win 100 points! Only one target per message! ",
                            description="",
                        ).parse(),
                        CommandExample(
                            None,
                            "Emote bingo for 222 points",
                            chat="user:!bingo emotes 222\n"
                            "bot: A bingo has started! Guess the right target to win 222 points! Only one target per message! ",
                            description="",
                        ).parse(),
                    ],
                ),
                "cancel": Command.raw_command(
                    self.bingo_cancel,
                    level=500,
                    delay_all=15,
                    delay_user=15,
                    description="Cancel a running bingo",
                    examples=[
                        CommandExample(
                            None,
                            "Cancel a bingo",
                            chat="user:!bingo cancel\n" "bot: Bingo cancelled by pajlada FeelsBadMan",
                            description="",
                        ).parse()
                    ],
                ),
                "help": Command.raw_command(
                    self.bingo_help_random,
                    level=500,
                    delay_all=15,
                    delay_user=15,
                    description="The bot will help the chat with a random letter from the bingo target",
                    examples=[
                        CommandExample(
                            None,
                            "Get a random letter from the bingo target",
                            chat="user:!bingo help\n"
                            "bot: A bingo for 100 points is still running. You should maybe use a a a a a for the target",
                            description="",
                        ).parse()
                    ],
                ),
                "cheat": Command.raw_command(
                    self.bingo_help_first,
                    level=500,
                    delay_all=15,
                    delay_user=15,
                    description="The bot will help the chat with the first letter from the bingo target",
                    examples=[
                        CommandExample(
                            None,
                            "Get the first letter from the bingo target",
                            chat="user:!bingo cheat\n"
                            "bot: A bingo for 100 points is still running. You should use W W W W W as the first letter for the target",
                            description="",
                        ).parse()
                    ],
                ),
            },
        )

    def enable(self, bot):
        HandlerManager.add_handler("on_message", self.on_message)

    def disable(self, bot):
        HandlerManager.remove_handler("on_message", self.on_message)

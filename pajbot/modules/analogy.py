import logging

import random

from pajbot.models.command import Command
from pajbot.models.command import CommandExample
from pajbot.modules import BaseModule
from pajbot.modules import ModuleSetting

log = logging.getLogger(__name__)


class AnalogyModule(BaseModule):

    ID = __name__.split(".")[-1]
    NAME = "Analogy"
    DESCRIPTION = "Gives users access to the !analogy command!"
    CATEGORY = "Game"
    SETTINGS = [
        ModuleSetting(
            key="online_global_cd",
            label="Global cooldown (seconds)",
            type="number",
            required=True,
            placeholder="",
            default=15,
            constraints={"min_value": 0, "max_value": 120},
        ),
        ModuleSetting(
            key="online_user_cd",
            label="Per-user cooldown (seconds)",
            type="number",
            required=True,
            placeholder="",
            default=30,
            constraints={"min_value": 0, "max_value": 240},
        ),
        ModuleSetting(
            key="analogies",
            label="List of analogies (separated by comma)",
            type="text",
            required=True,
            placeholder="https://clips.twitch.tv/BetterTenuousVultureCorgiDerp,https://clips.twitch.tv/SuperZealousSpaghettiBatChest",
            default="https://clips.twitch.tv/BetterTenuousVultureCorgiDerp,https://clips.twitch.tv/SuperZealousSpaghettiBatChest",
        ),
    ]

    def analogy_command(self, bot, source, message, **rest):
        analogyArray = self.settings["analogies"].split(",")
        analogy = random.choice(analogyArray)
        bot.say(f"{source}, {analogy}")

    def load_commands(self, **options):
        self.commands["analogy"] = Command.raw_command(
            self.analogy_command,
            delay_all=self.settings["online_global_cd"],
            delay_user=self.settings["online_user_cd"],
            description=f"Outputs a random analogy from {self.bot.streamer if self.bot else 'the streamer'}",
            examples=[
                CommandExample(
                    None,
                    "!analogy",
                    chat="user:!analogy\n" "bot:troydota, https://clips.twitch.tv/BetterTenuousVultureCorgiDerp",
                    description="Get an analogy",
                ).parse()
            ],
        )

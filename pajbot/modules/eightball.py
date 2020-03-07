import logging

import random

from pajbot.models.command import Command
from pajbot.models.command import CommandExample
from pajbot.modules import BaseModule
from pajbot.modules import ModuleSetting

log = logging.getLogger(__name__)


class EightBallModule(BaseModule):

    ID = __name__.split(".")[-1]
    NAME = "8-ball"
    DESCRIPTION = "Gives users access to the !8ball command!"
    CATEGORY = "Game"
    SETTINGS = [
        ModuleSetting(
            key="online_global_cd",
            label="Global cooldown (seconds)",
            type="number",
            required=True,
            placeholder="",
            default=4,
            constraints={"min_value": 0, "max_value": 120},
        ),
        ModuleSetting(
            key="online_user_cd",
            label="Per-user cooldown (seconds)",
            type="number",
            required=True,
            placeholder="",
            default=10,
            constraints={"min_value": 0, "max_value": 240},
        ),
    ]

    def __init__(self, bot):
        super().__init__(bot)
        self.phrases = [
            "sure",
            "are you kidding?!",
            "yeah",
            "no",
            "i think so",
            "don't bet on it",
            "ja",
            "doubtful",
            "for sure",
            "forget about it",
            "nein",
            "maybe",
            "Kappa Keepo PogChamp",
            "sure",
            "i dont think so",
            "it is so",
            "leaning towards no",
            "look deep in your heart and you will see the answer",
            "most definitely",
            "most likely",
            "my sources say yes",
            "never",
            "nah m8",
            "might actually be yes",
            "no.",
            "outlook good",
            "outlook not so good",
            "perhaps",
            "mayhaps",
            "that's a tough one",
            "idk kev",
            "don't ask that",
            "the answer to that isn't pretty",
            "the heavens point to yes",
            "who knows?",
            "without a doubt",
            "yesterday it would've been a yes, but today it's a yep",
            "you will have to wait",
        ]

        self.emotes = [
            "Kappa",
            "Keepo",
            "xD",
            "KKona",
            "4Head",
            "EleGiggle",
            "DansGame",
            "KappaCool",
            "BrokeBack",
            "OpieOP",
            "KappaRoss",
            "KappaPride",
            "FeelsBadMan",
            "FeelsGoodMan",
            "PogChamp",
            "VisLaud",
            "OhMyDog",
            "FrankerZ",
            "DatSheffy",
            "BabyRage",
            "VoHiYo",
            "haHAA",
            "FeelsBirthdayMan",
            "LUL",
        ]

    def eightball_command(self, bot, source, message, **rest):
        if not message or len(message) <= 0:
            return False

        phrase = random.choice(self.phrases)
        emote = random.choice(self.emotes)
        bot.me(f"{source}, the 8-ball says... {phrase} {emote}")

    def load_commands(self, **options):
        self.commands["8ball"] = Command.raw_command(
            self.eightball_command,
            delay_all=self.settings["online_global_cd"],
            delay_user=self.settings["online_user_cd"],
            description="Need help with a decision? Use the !8ball command!",
            examples=[
                CommandExample(
                    None,
                    "!8ball",
                    chat="user:!8ball Should I listen to gachimuchi?\n"
                    "bot:pajlada, the 8-ball says... Of course you should!",
                    description="Ask the 8ball an important question",
                ).parse()
            ],
        )

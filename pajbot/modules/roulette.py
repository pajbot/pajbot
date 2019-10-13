import datetime
import logging

import random

import pajbot.exc
import pajbot.models
from pajbot import utils
from pajbot.managers.db import DBManager
from pajbot.managers.handler import HandlerManager
from pajbot.models.command import Command
from pajbot.models.command import CommandExample
from pajbot.models.roulette import Roulette
from pajbot.modules import BaseModule
from pajbot.modules import ModuleSetting

log = logging.getLogger(__name__)


class RouletteModule(BaseModule):

    ID = __name__.split(".")[-1]
    NAME = "Roulette"
    DESCRIPTION = "Lets players roulette with themselves for points"
    CATEGORY = "Game"
    SETTINGS = [
        ModuleSetting(
            key="message_won",
            label="Won message | Available arguments: {bet}, {points}, {user}",
            type="text",
            required=True,
            placeholder="{user} won {bet} points in roulette and now has {points} points! FeelsGoodMan",
            default="{user} won {bet} points in roulette and now has {points} points! FeelsGoodMan",
            constraints={"min_str_len": 10, "max_str_len": 400},
        ),
        ModuleSetting(
            key="message_lost",
            label="Lost message | Available arguments: {bet}, {points}, {user}",
            type="text",
            required=True,
            placeholder="{user} lost {bet} points in roulette and now has {points} points! FeelsBadMan",
            default="{user} lost {bet} points in roulette and now has {points} points! FeelsBadMan",
            constraints={"min_str_len": 10, "max_str_len": 400},
        ),
        ModuleSetting(
            key="rigged_percentage",
            label="Rigged %, lower = more chance of winning. 50 = 50% of winning. 25 = 75% of winning",
            type="number",
            required=True,
            placeholder="",
            default=50,
            constraints={"min_value": 1, "max_value": 100},
        ),
        ModuleSetting(
            key="online_global_cd",
            label="Global cooldown (seconds)",
            type="number",
            required=True,
            placeholder="",
            default=0,
            constraints={"min_value": 0, "max_value": 120},
        ),
        ModuleSetting(
            key="online_user_cd",
            label="Per-user cooldown (seconds)",
            type="number",
            required=True,
            placeholder="",
            default=60,
            constraints={"min_value": 0, "max_value": 240},
        ),
        ModuleSetting(
            key="min_roulette_amount",
            label="Minimum roulette amount",
            type="number",
            required=True,
            placeholder="",
            default=1,
            constraints={"min_value": 1, "max_value": 3000},
        ),
        ModuleSetting(
            key="can_execute_with_whisper",
            label="Allow users to roulette in whispers",
            type="boolean",
            required=True,
            default=False,
        ),
        ModuleSetting(
            key="options_output",
            label="Result output options",
            type="options",
            required=True,
            default="1. Show results in chat",
            options=[
                "1. Show results in chat",
                "2. Show results in whispers",
                "3. Show results in chat if it's over X points else it will be whispered.",
                "4. Combine output in chat",
            ],
        ),
        ModuleSetting(
            key="min_show_points",
            label="Min points you need to win or lose (if options 3)",
            type="number",
            required=True,
            placeholder="",
            default=100,
            constraints={"min_value": 1, "max_value": 150000},
        ),
        ModuleSetting(
            key="only_roulette_after_sub",
            label="Only allow roulettes after sub",
            type="boolean",
            required=True,
            default=False,
        ),
        ModuleSetting(
            key="after_sub_roulette_time",
            label="How long after a sub people can roulette (seconds)",
            type="number",
            required=True,
            placeholder="",
            default=30,
            constraints={"min_value": 5, "max_value": 3600},
        ),
    ]

    def __init__(self, bot):
        super().__init__(bot)
        self.last_sub = None
        self.output_buffer = ""
        self.output_buffer_args = []
        self.last_add = None

    def load_commands(self, **options):
        self.commands["roulette"] = Command.raw_command(
            self.roulette,
            delay_all=self.settings["online_global_cd"],
            delay_user=self.settings["online_user_cd"],
            description="Roulette for points",
            can_execute_with_whisper=self.settings["can_execute_with_whisper"],
            examples=[
                CommandExample(
                    None,
                    "Roulette for 69 points",
                    chat="user:!roulette 69\n" "bot:pajlada won 69 points in roulette! FeelsGoodMan",
                    description="Do a roulette for 69 points",
                ).parse()
            ],
        )

    def rigged_random_result(self):
        return random.randint(1, 100) > self.settings["rigged_percentage"]

    def roulette(self, bot, source, message, **rest):
        if self.settings["only_roulette_after_sub"]:
            if self.last_sub is None:
                return False
            if utils.now() - self.last_sub > datetime.timedelta(seconds=self.settings["after_sub_roulette_time"]):
                return False

        if message is None:
            bot.whisper(source, "I didn't recognize your bet! Usage: !roulette 150 to bet 150 points")
            return False

        msg_split = message.split(" ")
        try:
            bet = utils.parse_points_amount(source, msg_split[0])
        except pajbot.exc.InvalidPointAmount as e:
            bot.whisper(source, str(e))
            return False

        if not source.can_afford(bet):
            bot.whisper(source, f"You don't have enough points to do a roulette for {bet} points :(")
            return False

        if bet < self.settings["min_roulette_amount"]:
            bot.whisper(source, f"You have to bet at least {self.settings['min_roulette_amount']} point! :(")
            return False

        # Calculating the result
        result = self.rigged_random_result()
        points = bet if result else -bet
        source.points += points

        with DBManager.create_session_scope() as db_session:
            r = Roulette(source.id, points)
            db_session.add(r)

        arguments = {"bet": bet, "user": source.name, "points": source.points, "win": points > 0}

        if points > 0:
            out_message = self.get_phrase("message_won", **arguments)
        else:
            out_message = self.get_phrase("message_lost", **arguments)

        if self.settings["options_output"] == "4. Combine output in chat":
            if bot.is_online:
                self.add_message(bot, arguments)
            else:
                bot.me(out_message)
        if self.settings["options_output"] == "1. Show results in chat":
            bot.me(out_message)
        if self.settings["options_output"] == "2. Show results in whispers":
            bot.whisper(source, out_message)
        if (
            self.settings["options_output"]
            == "3. Show results in chat if it's over X points else it will be whispered."
        ):
            if abs(points) >= self.settings["min_show_points"]:
                bot.me(out_message)
            else:
                bot.whisper(source, out_message)

        HandlerManager.trigger("on_roulette_finish", user=source, points=points)

    def on_tick(self, **rest):
        if self.output_buffer == "":
            return

        if self.last_add is None:
            return

        diff = utils.now() - self.last_add

        if diff.seconds > 3:
            self.flush_output_buffer()

    def flush_output_buffer(self):
        msg = self.output_buffer
        self.bot.me(msg)
        self.output_buffer = ""
        self.output_buffer_args = []

    def add_message(self, bot, arguments):
        parts = []
        new_buffer = "Roulette: "
        win_emote = "forsenPls"
        lose_emote = "forsenSWA"
        for arg in self.output_buffer_args:
            parts.append(
                f"{win_emote if arg['win'] else lose_emote} {arg['user']} {'+' if arg['win'] else '-'}{arg['bet']}"
            )

        parts.append(
            f"{win_emote if arguments['win'] else lose_emote} {arguments['user']} {'+' if arguments['win'] else '-'}{arguments['bet']}"
        )

        log.debug(parts)
        new_buffer += ", ".join(parts)

        if len(new_buffer) > 480:
            self.flush_output_buffer()
        else:
            self.output_buffer = new_buffer
            log.info("Set output buffer to " + new_buffer)

        self.output_buffer_args.append(arguments)

        self.last_add = utils.now()

    def on_user_sub(self, **rest):
        self.last_sub = utils.now()
        if self.settings["only_roulette_after_sub"]:
            self.bot.say(f"Rouletting is now allowed for {self.settings['after_sub_roulette_time']} seconds! PogChamp")

    def on_user_resub(self, **rest):
        self.last_sub = utils.now()
        if self.settings["only_roulette_after_sub"]:
            self.bot.say(f"Rouletting is now allowed for {self.settings['after_sub_roulette_time']} seconds! PogChamp")

    def enable(self, bot):
        HandlerManager.add_handler("on_user_sub", self.on_user_sub)
        HandlerManager.add_handler("on_user_resub", self.on_user_resub)
        HandlerManager.add_handler("on_tick", self.on_tick)

    def disable(self, bot):
        HandlerManager.remove_handler("on_user_sub", self.on_user_sub)
        HandlerManager.remove_handler("on_user_resub", self.on_user_resub)
        HandlerManager.remove_handler("on_tick", self.on_tick)

import datetime
import logging
import random
from collections import Counter

import pajbot.exc
import pajbot.models
import pajbot.utils
from pajbot import utils
from pajbot.managers.handler import HandlerManager
from pajbot.models.command import Command, CommandExample
from pajbot.modules import BaseModule, ModuleSetting

log = logging.getLogger(__name__)


# pull_lol returns the: (bet_return, emotes)
def pull_lol(low_tier_emotes, high_tier_emotes, bet, house_edge, ltsw, htsw, ltbw, htbw):
    slot_options = []
    for e in low_tier_emotes:
        slot_options += [e] * 3
    for e in high_tier_emotes:
        slot_options += [e]

    randomized_emotes = random.choices(slot_options, k=3)

    # figure out results of these randomized emotes xd
    bet_return = 0.0

    emote_counts = Counter(randomized_emotes)

    for emote_name in emote_counts:
        emote_count = emote_counts[emote_name]

        if emote_count <= 1:
            continue

        if emote_count == 2:
            # small win
            if emote_name in low_tier_emotes:
                bet_return += ltsw
            else:
                bet_return += htsw

        if emote_count == 3:
            # big win
            if emote_name in low_tier_emotes:
                bet_return += ltbw
            else:
                bet_return += htbw

    return bet_return, randomized_emotes


class SlotMachineModule(BaseModule):

    ID = __name__.split(".")[-1]
    NAME = "Slot Machine"
    DESCRIPTION = "Lets players play slot machines for points"
    CATEGORY = "Game"
    SETTINGS = [
        ModuleSetting(
            key="message_won",
            label="Won message | Available arguments: {bet}, {points}, {user}, {emotes}, {result}",
            type="text",
            required=True,
            placeholder="{user} | {emotes} | won {result} points PogChamp",
            default="{user} | {emotes} | won {result} points PogChamp",
            constraints={"min_str_len": 10, "max_str_len": 400},
        ),
        ModuleSetting(
            key="message_lost",
            label="Lost message | Available arguments: {bet}, {points}, {user}, {emotes}",
            type="text",
            required=True,
            placeholder="{user} | {emotes} | lost {bet} points LUL",
            default="{user} | {emotes} | lost {bet} points LUL",
            constraints={"min_str_len": 10, "max_str_len": 400},
        ),
        ModuleSetting(
            key="low_tier_emotes",
            label="Low tier emotes, space-separated. Low-tier emote are 3 times as likely to appear as high tier emotes (they get 3 slots compared to high emotes 1 slot per roll)",
            type="text",
            required=True,
            placeholder="KKona 4Head NaM",
            default="KKona 4Head NaM",
            constraints={"min_str_len": 0, "max_str_len": 400},
        ),
        ModuleSetting(
            key="high_tier_emotes",
            label="High tier emotes, space-separated",
            type="text",
            required=True,
            placeholder="OpieOP EleGiggle",
            default="OpieOP EleGiggle",
            constraints={"min_str_len": 0, "max_str_len": 400},
        ),
        ModuleSetting(
            key="ltsw",
            label="Low tier small win (Percentage) 22.6% with 2 low 2 high",
            type="number",
            required=True,
            placeholder="",
            default=125,
            constraints={"min_value": 0, "max_value": 1000000},
        ),
        ModuleSetting(
            key="ltbw",
            label="Low tier big win (Percentage) 0.98% with 2 low 2 high",
            type="number",
            required=True,
            placeholder="",
            default=175,
            constraints={"min_value": 0, "max_value": 1000000},
        ),
        ModuleSetting(
            key="htsw",
            label="High tier small win (Percentage) 0.14% with 2 low 2 high",
            type="number",
            required=True,
            placeholder="",
            default=225,
            constraints={"min_value": 0, "max_value": 1000000},
        ),
        ModuleSetting(
            key="htbw",
            label="High tier big win (Percentage) 0.07% with 2 low 2 high",
            type="number",
            required=True,
            placeholder="",
            default=400,
            constraints={"min_value": 0, "max_value": 1000000},
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
            key="min_bet",
            label="Minimum bet",
            type="number",
            required=True,
            placeholder="",
            default=1,
            constraints={"min_value": 1, "max_value": 1000000},
        ),
        ModuleSetting(
            key="can_execute_with_whisper",
            label="Allow users to use the module from whispers",
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
            constraints={"min_value": 1, "max_value": 1000000},
        ),
        ModuleSetting(
            key="only_slots_after_sub",
            label="Only allow slots after sub",
            type="boolean",
            required=True,
            default=False,
        ),
        ModuleSetting(
            key="after_sub_slots_time",
            label="How long after a sub people can use the slot machine (seconds)",
            type="number",
            required=True,
            placeholder="",
            default=30,
            constraints={"min_value": 5, "max_value": 3600},
        ),
        ModuleSetting(
            key="alert_message_after_sub",
            label="Message to announce the allowance of slotmachine usage after re/sub, leave empty to disable the message. | Available arguments: {seconds}",
            type="text",
            required=True,
            default="Slot machine is now allowed for {seconds} seconds! PogChamp",
            constraints={"min_str_len": 0, "max_str_len": 300},
        ),
    ]

    def __init__(self, bot):
        super().__init__(bot)
        self.last_sub = None
        self.output_buffer = ""
        self.output_buffer_args = []
        self.last_add = None

    def load_commands(self, **options):
        self.commands["slotmachine"] = Command.raw_command(
            self.pull,
            delay_all=self.settings["online_global_cd"],
            delay_user=self.settings["online_user_cd"],
            description="play slot machine for points",
            can_execute_with_whisper=self.settings["can_execute_with_whisper"],
            examples=[
                CommandExample(
                    None,
                    "SlotMachine for 69 points",
                    chat="user:!slotmachine 69\n" "bot:pajlada won 69 points in slotmachine xd! FeelsGoodMan",
                    description="Do a slot machine pull for 69 points",
                ).parse()
            ],
        )
        self.commands["smp"] = self.commands["slotmachine"]
        self.commands["slots"] = self.commands["slotmachine"]

    def pull(self, bot, source, message, **rest):
        if self.settings["only_slots_after_sub"]:
            if self.last_sub is None:
                return False
            if utils.now() - self.last_sub > datetime.timedelta(seconds=self.settings["after_sub_slots_time"]):
                return False

        if message is None:
            bot.whisper(source, "I didn't recognize your bet! Usage: !slotmachine 150 to bet 150 points")
            return False

        low_tier_emotes = self.settings["low_tier_emotes"].split()
        high_tier_emotes = self.settings["high_tier_emotes"].split()

        if len(low_tier_emotes) == 0 or len(high_tier_emotes) == 0:
            return False

        msg_split = message.split(" ")
        try:
            bet = pajbot.utils.parse_points_amount(source, msg_split[0])
        except pajbot.exc.InvalidPointAmount as e:
            bot.whisper(source, str(e))
            return False

        if not source.can_afford(bet):
            bot.whisper(source, f"You don't have enough points to do a slot machine pull for {bet} points :(")
            return False

        if bet < self.settings["min_bet"]:
            bot.whisper(source, f"You have to bet at least {self.settings['min_bet']} point! :(")
            return False

        # how much of the users point they're expected to get back (basically how much the house yoinks)
        expected_return = 1.0

        ltsw = self.settings["ltsw"] / 100.0
        htsw = self.settings["htsw"] / 100.0
        ltbw = self.settings["ltbw"] / 100.0
        htbw = self.settings["htbw"] / 100.0

        bet_return, randomized_emotes = pull_lol(
            low_tier_emotes, high_tier_emotes, bet, expected_return, ltsw, htsw, ltbw, htbw
        )

        # Calculating the result
        if bet_return <= 0.0:
            points = -bet
        else:
            points = bet * bet_return

        source.points += points

        arguments = {
            "bet": bet,
            "result": points,
            "user": source.name,
            "points": source.points,
            "win": points > 0,
            "emotes": " ".join(randomized_emotes),
        }

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

        HandlerManager.trigger("on_slot_machine_finish", user=source, points=points)

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
        new_buffer = "SlotMachine: "
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

    def on_user_sub_or_resub(self, **rest):
        now = utils.now()

        # True if we already announced the alert_message_after_sub within the last 5 seconds. Prevents
        # spam after bulk sub gifts.
        skip_message = self.last_sub is not None and now - self.last_sub < datetime.timedelta(seconds=5)

        self.last_sub = now
        if (
            self.settings["only_slots_after_sub"]
            and self.settings["alert_message_after_sub"] != ""
            and not skip_message
        ):
            self.bot.say(self.settings["alert_message_after_sub"].format(seconds=self.settings["after_sub_slots_time"]))

    def enable(self, bot):
        HandlerManager.add_handler("on_user_sub", self.on_user_sub_or_resub)
        HandlerManager.add_handler("on_user_resub", self.on_user_sub_or_resub)
        HandlerManager.add_handler("on_tick", self.on_tick)

    def disable(self, bot):
        HandlerManager.remove_handler("on_user_sub", self.on_user_sub_or_resub)
        HandlerManager.remove_handler("on_user_resub", self.on_user_sub_or_resub)
        HandlerManager.remove_handler("on_tick", self.on_tick)

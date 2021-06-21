import logging

import random
import re

from pajbot.managers.handler import HandlerManager
from pajbot.models.command import Command
from pajbot.models.command import CommandExample
from pajbot.modules import BaseModule
from pajbot.modules import ModuleSetting
from pajbot.utils import iterate_split_with_index

log = logging.getLogger(__name__)


class BingoGame:
    def __init__(self, correct_emote, points_reward):
        self.correct_emote = correct_emote
        self.points_reward = points_reward


def two_word_variations(word1, word2, value):
    # this produces:
    # bttv_global
    # global_bttv
    # bttv-global
    # global-bttv
    # bttvglobal
    # globalbttv
    variations = [
        f"{word1}_{word2}",
        f"{word2}_{word1}",
        f"{word1}-{word2}",
        f"{word2}-{word1}",
        f"{word1}{word2}",
        f"{word2}{word1}",
    ]

    return {key: value for key in variations}


def join_to_sentence(list, sep=", ", last_sep=" and "):
    if len(list) == 0:
        return ""

    if len(list) == 1:
        return list[0]

    return last_sep.join([sep.join(list[:-1]), list[-1]])


remove_emotes_suffix_regex = re.compile(r"^(.*?)(?:[-_]?emotes?)?$", re.IGNORECASE)


def remove_emotes_suffix(word):
    match = remove_emotes_suffix_regex.match(word)
    if not match:
        # the regex has a .* in it which means it should match anything O_o
        raise ValueError("That doesn't match my regex O_o")

    return match.group(1)


class BingoModule(BaseModule):
    ID = __name__.split(".")[-1]
    NAME = "Bingo"
    DESCRIPTION = "Chat Bingo Game for Twitch, FFZ, BTTV and 7TV Emotes"
    ENABLED_DEFAULT = False
    CATEGORY = "Game"
    SETTINGS = [
        ModuleSetting(
            key="default_points",
            label="Defaults points reward for a bingo",
            type="number",
            required=True,
            placeholder="",
            default=100,
            constraints={"min_value": 0, "max_value": 35000},
        ),
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

    @property
    def bingo_running(self):
        return self.active_game is not None

    @staticmethod
    def make_twitch_sets(manager):
        tier_one_emotes = ("Tier 1 sub emotes", manager.tier_one_emotes)
        tier_two_emotes = ("Tier 2 sub emotes", manager.tier_two_emotes)
        tier_three_emotes = ("Tier 3 sub emotes", manager.tier_three_emotes)
        global_emotes = ("Global Twitch emotes", manager.global_emotes)
        all_emotes = ("Global + Twitch tier 1 sub emotes", manager.tier_one_emotes + manager.global_emotes)
        return {
            "twitch": tier_one_emotes,
            "sub": tier_one_emotes,
            "tier1": tier_one_emotes,
            "tier2": tier_two_emotes,
            "tier3": tier_three_emotes,
            **two_word_variations("twitch", "sub", tier_one_emotes),
            **two_word_variations("twitch", "tier1", tier_one_emotes),
            **two_word_variations("twitch", "tier2", tier_two_emotes),
            **two_word_variations("twitch", "tier3", tier_three_emotes),
            **two_word_variations("twitch", "global", global_emotes),
            **two_word_variations("twitch", "channel", tier_one_emotes),
            **two_word_variations("twitch", "all", all_emotes),
        }

    @staticmethod
    def make_bttv_ffz_7tv_sets(manager):
        friendly_name = manager.friendly_name
        channel_emotes = (f"Channel {friendly_name} emotes", manager.channel_emotes)
        global_emotes = (f"Global {friendly_name} emotes", manager.global_emotes)
        all_emotes = (f"Global + Channel {friendly_name} emotes", manager.channel_emotes + manager.global_emotes)

        key = friendly_name.lower()
        return {
            key: channel_emotes,
            **two_word_variations(key, "global", global_emotes),
            **two_word_variations(key, "channel", channel_emotes),
            **two_word_variations(key, "all", all_emotes),
        }

    def make_known_sets_dict(self):
        # we first make a dict containing lists as the list of emotes (because it's less to type...)
        list_dict = {
            **self.make_twitch_sets(self.bot.emote_manager.twitch_emote_manager),
            **self.make_bttv_ffz_7tv_sets(self.bot.emote_manager.ffz_emote_manager),
            **self.make_bttv_ffz_7tv_sets(self.bot.emote_manager.bttv_emote_manager),
            **self.make_bttv_ffz_7tv_sets(self.bot.emote_manager.seventv_emote_manager),
            "all": (
                "FFZ, BTTV and 7TV Channel emotes + Tier 1 subemotes",
                self.bot.emote_manager.ffz_emote_manager.channel_emotes
                + self.bot.emote_manager.bttv_emote_manager.channel_emotes
                + self.bot.emote_manager.seventv_emote_manager.channel_emotes
                + self.bot.emote_manager.twitch_emote_manager.tier_one_emotes,
            ),
        }

        # then convert all the lists to tuples so they are hashable
        # and can be stored in a set of "selected sets" later
        return {key: (set_name, tuple(set_emotes), False) for key, (set_name, set_emotes) in list_dict.items()}

    def bingo_start(self, bot, source, message, event, args):
        if self.bingo_running:
            bot.say(f"{source}, a bingo is already running FailFish")
            return False

        emote_instances = args["emote_instances"]
        known_sets = self.make_known_sets_dict()

        selected_sets = set()
        points_reward = None
        unparsed_options = []

        words_in_message = [s for s in message.split(" ") if len(s) > 0]
        if len(words_in_message) <= 0:
            bot.say(f"{source}, You must at least give me some emote sets or emotes to choose from! FailFish")
            return False

        emote_index_offset = len("!bingo start ")

        # we can't iterate using words_in_message here because that would mess up the accompanying index
        for index, word in iterate_split_with_index(message.split(" ")):
            if len(word) <= 0:
                continue

            # Is the current word an emote?
            potential_emote_instance = next((e for e in emote_instances if e.start == index + emote_index_offset), None)
            if potential_emote_instance is not None:
                # single-emote set with the name of the emote
                new_set = (potential_emote_instance.emote.code, (potential_emote_instance.emote,), True)
                selected_sets.add(new_set)
                continue

            # Is the current word a number?
            try:
                parsed_int = int(word)
            except ValueError:
                parsed_int = None

            if parsed_int is not None:
                # if points_reward is already set this is the second number in the message
                if points_reward is not None:
                    unparsed_options.append(word)
                    continue
                points_reward = parsed_int
                continue

            # Is the current word a known set?
            cleaned_key = remove_emotes_suffix(word).lower()
            if cleaned_key in known_sets:
                selected_sets.add(known_sets[cleaned_key])
                continue

            unparsed_options.append(word)

        if len(unparsed_options) > 0:
            bot.say(
                "{}, I don't know what to do with the argument{} {} BabyRage".format(
                    source,
                    "" if len(unparsed_options) == 1 else "s",  # pluralization
                    join_to_sentence(['"' + s + '"' for s in unparsed_options]),
                )
            )
            return False

        default_points = self.settings["default_points"]
        if points_reward is None:
            points_reward = default_points

        max_points = self.settings["max_points"]
        if points_reward > max_points:
            bot.say(
                f"{source}, You can't start a bingo with that many points. FailFish {max_points} are allowed at most."
            )
            return False

        allow_negative_bingo = self.settings["allow_negative_bingo"]
        if points_reward < 0 and not allow_negative_bingo:
            bot.say(f"{source}, You can't start a bingo with negative points. FailFish")
            return False

        min_points = -self.settings["max_negative_points"]
        if points_reward < min_points:
            bot.say(
                f"{source}, You can't start a bingo with that many negative points. FailFish {min_points} are allowed at most."
            )
            return False

        if len(selected_sets) <= 0:
            bot.say(f"{source}, You must at least give me some emotes or emote sets to choose from! FailFish")
            return False

        selected_set_names = []
        selected_discrete_emote_codes = []
        selected_emotes = set()
        for set_name, set_emotes, is_discrete_emote in selected_sets:
            if is_discrete_emote:
                selected_discrete_emote_codes.append(set_name)
            else:
                selected_set_names.append(set_name)
            selected_emotes.update(set_emotes)

        correct_emote = random.choice(list(selected_emotes))

        user_messages = []
        if len(selected_set_names) > 0:
            user_messages.append(join_to_sentence(selected_set_names))

        if len(selected_discrete_emote_codes) > 0:
            # the space at the end is so the ! from the below message doesn't stop the last emote from showing up in chat
            user_messages.append(f"these emotes: {' '.join(selected_discrete_emote_codes)} ")

        bot.me(
            f"A bingo has started! ThunBeast Guess the right emote to win {points_reward} points! B) Only one emote per message! Select from {' and '.join(user_messages)}!"
        )

        log.info(f"A Bingo game has begun for {points_reward} points, correct emote is {correct_emote}")
        self.active_game = BingoGame(correct_emote, points_reward)

    def bingo_cancel(self, bot, source, message, event, args):
        if not self.bingo_running:
            bot.say(f"{source}, no bingo is running FailFish")
            return False

        self.active_game = None
        bot.me(f"Bingo cancelled by {source} FeelsBadMan")

    def bingo_help_random(self, bot, source, message, event, args):
        if not self.bingo_running:
            bot.say(f"{source}, no bingo is running FailFish")
            return False

        correct_emote_code = self.active_game.correct_emote.code
        random_letter = random.choice(correct_emote_code)

        bot.me(
            f"A bingo for {self.active_game.points_reward} points is still running. You should maybe use {random_letter} {random_letter} {random_letter} {random_letter} {random_letter} for the target"
        )

    def bingo_help_first(self, bot, source, message, event, args):
        if not self.bingo_running:
            bot.say(f"{source}, no bingo is running FailFish")
            return False

        correct_emote_code = self.active_game.correct_emote.code
        first_letter = correct_emote_code[0]

        bot.me(
            f"A bingo for {self.active_game.points_reward} points is still running. You should maybe use {first_letter} {first_letter} {first_letter} {first_letter} {first_letter} for the target"
        )

    def on_message(self, source, message, emote_instances, **rest):
        if not self.bingo_running:
            return

        if len(emote_instances) != 1:
            return

        correct_emote = self.active_game.correct_emote
        correct_emote_code = correct_emote.code

        typed_emote = emote_instances[0].emote
        typed_emote_code = typed_emote.code

        # we check for BOTH exact match (which works by comparing provider and ID, see __eq__ and __hash__ in
        # the Emote class) and for code-only match because we want to allow equal-named sub and ffz/bttv/7tv emotes
        # to be treated equally (e.g. sub-emote pajaL vs bttv emote pajaL)
        # The reason exact match can differ from code match is in case of regex twitch emotes, such as :) and :-)
        # If the "correct_emote" was chosen from the list of global twitch emotes, then its code will be the regex
        # for the emote (If the bingo was started by specifying :) as an explicit emote, then the code will be
        # :)). To make sure we don't trip on this we only compare by provider and provider ID.
        exact_match = correct_emote == typed_emote
        only_code_match = correct_emote_code == typed_emote_code
        if not (exact_match or only_code_match):
            return

        # user guessed the emote
        HandlerManager.trigger("on_bingo_win", source, self.active_game)
        points_reward = self.active_game.points_reward
        source.points += points_reward
        self.active_game = None

        self.bot.me(
            f"{source} won the bingo! {correct_emote_code} was the target. Congrats, {points_reward} points to you PogChamp"
        )

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
                            "Emote bingo for default points",
                            chat="user:!bingo start bttv\n"
                            "bot: A bingo has started! Guess the right target to win 100 points! "
                            "Only one target per message! Select from Channel BTTV Emotes!",
                            description="",
                        ).parse(),
                        CommandExample(
                            None,
                            "Emote bingo for 222 points",
                            chat="user:!bingo start bttv 222\n"
                            "bot: A bingo has started! Guess the right target to win 222 points! "
                            "Only one target per message! Select from Channel BTTV Emotes!",
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

from __future__ import print_function

import logging

from pajbot.managers.handler import HandlerManager
from pajbot.modules import BaseModule, ModuleSetting

log = logging.getLogger(__name__)


class RepspamModule(BaseModule):

    ID = __name__.split(".")[-1]
    NAME = "Repetitive Spam"
    DESCRIPTION = "Times out messages containing repetitive spam"
    ENABLED_DEFAULT = False
    CATEGORY = "Moderation"
    SETTINGS = [
        ModuleSetting(
            key="enabled_by_stream_status",
            label="Enable moderation of repetitive spam when the stream is:",
            type="options",
            required=True,
            default="Offline and Online",
            options=["Online Only", "Offline Only", "Offline and Online"],
        ),
        ModuleSetting(
            key="bypass_level",
            label="Level to bypass module",
            type="number",
            required=True,
            placeholder="",
            default=420,
            constraints={"min_value": 100, "max_value": 2000},
        ),
        ModuleSetting(
            key="min_message_length",
            label="Minimum message length before it can be considered repetitive",
            type="number",
            required=True,
            placeholder="",
            default=50,
            constraints={"min_value": 0, "max_value": 500},
        ),
        ModuleSetting(
            key="min_unique_words",
            label="Minimum number of unique words required in message before it can be considered repetitive",
            type="number",
            required=True,
            placeholder="",
            default=3,
            constraints={"min_value": 1, "max_value": 100},
        ),
        ModuleSetting(
            key="max_spam_repetitions",
            label="Maximum number of times a spam may be repeated",
            type="number",
            required=True,
            placeholder="",
            default=4,
            constraints={"min_value": 1, "max_value": 100},
        ),
        ModuleSetting(
            key="min_unique_words_in_spam",
            label="Minimum number of unique words in a spam before it is considered repetitive",
            type="number",
            required=True,
            placeholder="",
            default=2,
            constraints={"min_value": 1, "max_value": 100},
        ),
        ModuleSetting(
            key="timeout_length",
            label="Timeout length",
            type="number",
            required=True,
            placeholder="Timeout length in seconds",
            default=10,
            constraints={"min_value": 1, "max_value": 1209600},
        ),
        ModuleSetting(
            key="timeout_reason",
            label="Timeout Reason",
            type="text",
            required=False,
            placeholder="",
            default="No repetitive messages OMGScoods",
            constraints={},
        ),
    ]

    def enable(self, bot):
        HandlerManager.add_handler("on_message", self.on_message, priority=150, run_if_propagation_stopped=True)

    def disable(self, bot):
        HandlerManager.remove_handler("on_message", self.on_message)

    ignored_characters = ["\U000e0000", ".", "-"]

    @staticmethod
    def is_word_ignored(word):
        for c in RepspamModule.ignored_characters:
            word = word.replace(c, "")

        word = word.strip()

        return len(word) <= 0

    def on_message(self, source, message, whisper, **rest):
        if self.settings["enabled_by_stream_status"] == "Online Only" and not self.bot.is_online:
            return

        if self.settings["enabled_by_stream_status"] == "Offline Only" and self.bot.is_online:
            return

        if whisper:
            return

        if source.level >= self.settings["bypass_level"] or source.moderator:
            return

        if len(message) < self.settings["min_message_length"]:
            # Message too short
            return

        word_list = [word for word in message.split(" ") if not self.is_word_ignored(word)]
        word_set = set(word_list)

        if len(word_set) < self.settings["min_unique_words"]:
            # There needs to be at least X unique words
            return

        # create a mapping word -> count/frequency
        word_freq = {word: word_list.count(word) for word in word_set}

        # reverse the mapping to frequency -> set of words that repeat that amount
        # (sorted by frequency, from most frequent to lowest frequent)
        freq_to_word = {}
        for word, freq in word_freq.items():
            freq_to_word.setdefault(freq, set()).add(word)

        # iterate frequency -> set of words ("group of words that repeat the same amount of times")
        for freq, words in freq_to_word.items():
            if len(words) < self.settings["min_unique_words_in_spam"]:
                continue

            if freq <= self.settings["max_spam_repetitions"]:
                continue

            # found a group of equally repeating words (a repeating spam) that repeats more than allowed
            self.bot.timeout(source, self.settings["timeout_length"], self.settings["timeout_reason"], once=True)
            return False

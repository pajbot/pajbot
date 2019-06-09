import json
import logging

from pajbot.managers.redis import RedisManager
from pajbot.modules.base import BaseModule
from pajbot.streamhelper import StreamHelper

log = logging.getLogger(__name__)


class BaseQuest(BaseModule):
    OBJECTIVE = "No objective set."

    def __init__(self, bot):
        super().__init__(bot)
        self.progress = {}
        self.progress_key = "{streamer}:current_quest_progress".format(streamer=StreamHelper.get_streamer())
        self.quest_finished_key = "{streamer}:quests:finished".format(streamer=StreamHelper.get_streamer())
        self.quest_module = None

    # TODO remove redis parameter
    def finish_quest(self, redis, user):
        if not self.quest_module:
            log.error("Quest module not initialized")
            return

        stream_id = StreamHelper.get_current_stream_id()

        # Load user's finished quest status
        val = redis.hget(self.quest_finished_key, user.username)
        if val:
            quests_finished = json.loads(val)
        else:
            quests_finished = []

        if stream_id in quests_finished:
            # User has already completed this quest
            return

        reward_type = self.quest_module.settings["reward_type"]
        reward_amount = self.quest_module.settings["reward_amount"]

        if reward_type == "tokens" and user.tokens > self.quest_module.settings["max_tokens"]:
            message = (
                "You finished todays quest, but you have more than the max tokens allowed already. Spend some tokens!"
            )
            self.bot.whisper(user.username, message)
            return

        # Mark the current stream ID has finished
        quests_finished.append(stream_id)
        redis.hset(self.quest_finished_key, user.username, json.dumps(quests_finished, separators=(",", ":")))

        # Award the user appropriately
        if reward_type == "tokens":
            user.tokens += reward_amount
        else:
            user.points += reward_amount

        # Notify the user that they've finished today's quest
        message = "You finished todays quest! You have been awarded with {} {}.".format(reward_amount, reward_type)
        self.bot.whisper(user.username, message)

        user.save()

    def start_quest(self):
        """ This method is triggered by either the stream starting, or the bot loading up
        while a quest/stream is already active """
        log.error("No start quest implemented for this quest.")

    def stop_quest(self):
        """ This method is ONLY called when the stream is stopped. """
        log.error("No stop quest implemented for this quest.")

    def get_user_progress(self, username, default=False):
        return self.progress.get(username, default)

    # TODO remove redis parameter
    def set_user_progress(self, username, new_progress, redis=None):
        if redis is None:
            redis = RedisManager.get()
        redis.hset(self.progress_key, username, new_progress)
        self.progress[username] = new_progress

    # TODO remove redis parameter
    def load_progress(self, redis=None):
        if redis is None:
            redis = RedisManager.get()
        self.progress = {}
        old_progress = redis.hgetall(self.progress_key)
        for user, progress in old_progress.items():
            try:
                self.progress[user] = int(progress)
            except (TypeError, ValueError):
                pass

    # TODO remove redis parameter
    def load_data(self, redis=None):
        """
        Useful base method for loading dynamic parts of the quest.
        For example, what emote is supposed to be used in the type emote quest
        """

    # TODO remove redis parameter
    def reset_progress(self, redis=None):
        if redis is None:
            redis = RedisManager.get()
        redis.delete(self.progress_key)

    def get_objective(self):
        return self.OBJECTIVE

    def get_limit(self):
        """ Returns the quest limit specified in the module.
        If no quest limit is set, return None. """

        try:
            return self.LIMIT
        except:
            return None

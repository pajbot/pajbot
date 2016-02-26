import logging

from pajbot.modules import BaseModule, ModuleSetting
from pajbot.streamhelper import StreamHelper
from pajbot.managers import RedisManager

log = logging.getLogger(__name__)

class BaseQuest(BaseModule):
    OBJECTIVE = 'No objective set.'

    def __init__(self):
        super().__init__()
        self.progress = {}
        self.progress_key = '{streamer}:current_quest_progress'.format(streamer=StreamHelper.get_streamer())

    def start_quest(self):
        """ This method is triggered by either the stream starting, or the bot loading up
        while a quest/stream is already active """
        log.error('No start quest implemented for this quest.')

    def stop_quest(self):
        """ This method is ONLY called when the stream is stopped. """
        log.error('No stop quest implemented for this quest.')

    def get_user_progress(self, username, default=False):
        return self.progress.get(username, default)

    def set_user_progress(self, username, new_progress, redis=None):
        if redis is None:
            redis = RedisManager.get()
        redis.hset(self.progress_key, username, new_progress)
        self.progress[username] = new_progress

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

    def load_data(self, redis=None):
        """
        Useful base method for loading dynamic parts of the quest.
        For example, what emote is supposed to be used in the type emote quest
        """
        pass

    def reset_progress(self, redis=None):
        if redis is None:
            redis = RedisManager.get()
        redis.delete(self.progress_key)

    def get_objective(self):
        return self.OBJECTIVE

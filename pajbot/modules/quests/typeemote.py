import logging

from pajbot.modules import BaseModule, ModuleSetting
from pajbot.modules import QuestModule
from pajbot.modules.quests import BaseQuest
from pajbot.managers import RedisManager
from pajbot.models.handler import HandlerManager
from pajbot.models.command import Command
from pajbot.streamhelper import StreamHelper

from numpy import random

log = logging.getLogger(__name__)

class TypeEmoteQuestModule(BaseQuest):

    ID = 'quest-' + __name__.split('.')[-1]
    NAME = 'Type X emote Y times'
    DESCRIPTION = 'A user needs to type a specific emote Y times to complete this quest.'
    PARENT_MODULE = QuestModule

    PROGRESS = 40
    LIMIT = 1
    REWARD = 3

    def __init__(self):
        super().__init__()
        self.current_emote_key = '{streamer}:current_quest_emote'.format(streamer=StreamHelper.get_streamer())
        self.current_emote = '???'
        self.progress = {}

    def on_message(self, source, message, emotes, whisper, urls):
        for emote in emotes:
            if emote['code'] == self.current_emote:
                if source.username in self.progress:
                    user_progress = self.progress[source.username] + 1
                else:
                    user_progress = 1

                if user_progress > self.PROGRESS:
                    # no need to do more
                    return

                self.progress[source.username] = user_progress

                redis = RedisManager.get()

                if user_progress == self.PROGRESS:
                    source.award_tokens(self.REWARD, redis=redis)

                redis.hset(self.progress_key, source.username, user_progress)
                return

    def start_quest(self):
        HandlerManager.add_handler('on_message', self.on_message)

        redis = RedisManager.get()

        self.progress = {}
        old_progress = redis.hgetall(self.progress_key)
        for user, progress in old_progress.items():
            try:
                self.progress[user.decode('utf8')] = int(progress)
            except (TypeError, ValueError):
                pass
        self.current_emote = redis.get(self.current_emote_key)
        if self.current_emote is None:
            # randomize an emote
            global_twitch_emotes = self.bot.emotes.get_global_emotes()
            self.current_emote = random.choice(global_twitch_emotes)
            redis.set(self.current_emote_key, self.current_emote)
        else:
            self.current_emote = self.current_emote.decode('utf8')

    def stop_quest(self):
        HandlerManager.remove_handler('on_message', self.on_message)

        redis = RedisManager.get()

        redis.delete(self.progress_key)
        redis.delete(self.current_emote_key)

    def get_objective(self):
        return 'Use the {} emote {} times'.format(self.current_emote, self.PROGRESS)

    def enable(self, bot):
        self.bot = bot

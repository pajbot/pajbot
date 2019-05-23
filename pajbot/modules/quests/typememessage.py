import logging

from pajbot.managers.handler import HandlerManager
from pajbot.managers.redis import RedisManager
from pajbot.modules import ModuleSetting
from pajbot.modules import QuestModule
from pajbot.modules.quests import BaseQuest

log = logging.getLogger(__name__)


class TypeMeMessageQuestModule(BaseQuest):

    ID = 'quest-' + __name__.split('.')[-1]
    NAME = 'Colorful chat /me'
    DESCRIPTION = 'Type X /me messages with X message length.'
    PARENT_MODULE = QuestModule
    CATEGORY = 'Quest'
    SETTINGS = [
            ModuleSetting(
                key='quest_limit',
                label='How many messages does the user needs to type?',
                type='number',
                required=True,
                placeholder='',
                default=100,
                constraints={
                    'min_value': 1,
                    'max_value': 200,
                    }),
            ModuleSetting(
                key='quest_message_length',
                label='How many letters minimum should be in the message?',
                type='number',
                required=True,
                placeholder='',
                default=15,
                constraints={
                    'min_value': 1,
                    'max_value': 500,
                    }),
            ]

    def get_limit(self):
        return self.settings['quest_limit']

    def get_quest_message_length(self):
        return self.settings['quest_message_length']

    def on_message(self, source, message, emotes, whisper, urls, event):
        if len(message) >= self.get_quest_message_length():
            if event.type == 'action':
                user_progress = self.get_user_progress(source.username, default=0)

                if user_progress >= self.get_limit():
                    return

                user_progress += 1

                redis = RedisManager.get()

                if user_progress == self.get_limit():
                    self.finish_quest(redis, source)

                self.set_user_progress(source.username, user_progress, redis=redis)

    def start_quest(self):
        HandlerManager.add_handler('on_message', self.on_message)

        redis = RedisManager.get()

        self.load_progress(redis=redis)

    def stop_quest(self):
        HandlerManager.remove_handler('on_message', self.on_message)

        redis = RedisManager.get()

        self.reset_progress(redis=redis)

    def get_objective(self):
        return 'Type {0} /me messages with a length of minimum {1} letters KappaPride '.format(self.get_limit(), self.get_quest_message_length())

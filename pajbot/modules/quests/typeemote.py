import logging

from pajbot.modules import BaseModule, ModuleSetting
from pajbot.modules import QuestModule
from pajbot.modules.quests import BaseQuest
from pajbot.models.handler import HandlerManager
from pajbot.models.command import Command

log = logging.getLogger(__name__)

class TypeEmoteQuestModule(BaseQuest):

    ID = 'quest-' + __name__.split('.')[-1]
    NAME = 'Type X emote Y times (WIP)'
    DESCRIPTION = 'A user needs to type a specific emote Y times to complete this quest.'
    PARENT_MODULE = QuestModule

    PROGRESS = 1
    LIMIT = 1
    REWARD = 3

    def on_message(self, source, message, emotes, whisper, urls):
        pass

    def start_quest(self):
        HandlerManager.add_handler('on_message', self.on_message)

    def stop_quest(self):
        HandlerManager.remove_handler('on_message', self.on_message)

    def get_objective(self):
        return 'asd'

    def enable(self, bot):
        self.bot = bot

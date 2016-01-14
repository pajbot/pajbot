import logging
import random

from pajbot.modules import BaseModule, ModuleSetting
from pajbot.models.command import Command
from pajbot.models.handler import HandlerManager

log = logging.getLogger(__name__)

class QuestModule(BaseModule):

    ID = __name__.split('.')[-1]
    NAME = 'Quest system'
    DESCRIPTION = 'Give users a single quest at the start of each day'
    SETTINGS = [
            ]

    def __init__(self):
        super().__init__()
        self.current_quest = None

    def load_commands(self, **options):
        # TODO: Add !currentquest command
        pass

    def on_stream_start(self):
        if len(self.submodules) == 0:
            log.error('No quests enabled.')
            return False

        self.current_quest = random.choice(self.submodules)
        self.current_quest.start_quest()
        self.bot.say('Stream started, new quest has been chosen!')
        self.bot.say('Current quest objective: {}'.format(self.current_quest.OBJECTIVE))

    def on_stream_stop(self):
        if self.current_quest is None:
            log.info('No quest active on stream stop.')
            return False

        self.current_quest.stop_quest()
        self.current_quest = None
        self.bot.say('Stream ended, quest has been reset.')

    def enable(self, bot):
        HandlerManager.add_handler('on_stream_start', self.on_stream_start)
        HandlerManager.add_handler('on_stream_stop', self.on_stream_stop)

        self.bot = bot

        # TODO: Check if we need to resume the quest from before stream crash?

    def disable(self, bot):
        HandlerManager.remove_handler('on_stream_start', self.on_stream_start)
        HandlerManager.remove_handler('on_stream_stop', self.on_stream_stop)

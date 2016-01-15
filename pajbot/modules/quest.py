import logging
import random

from pajbot.modules import BaseModule, ModuleSetting
from pajbot.models.command import Command
from pajbot.models.handler import HandlerManager
from pajbot.managers import RedisManager
from pajbot.tbutil import find

log = logging.getLogger(__name__)

class QuestModule(BaseModule):

    ID = __name__.split('.')[-1]
    NAME = 'Quest system'
    DESCRIPTION = 'Give users a single quest at the start of each day'
    SETTINGS = []

    def __init__(self):
        super().__init__()
        self.current_quest = None

    def my_progress(self, **options):
        bot = options['bot']
        source = options['source']
        if self.current_quest is not None:
            quest_progress = source.get_quest_progress(bot)
            if quest_progress is not False:
                bot.say('Your current quest progress is {}'.format(quest_progress))
            else:
                bot.say('You have no progress on the current quest.')
        else:
            bot.say('There is no quest active right now.')

    def get_current_quest(self, **options):
        bot = options['bot']
        if self.current_quest is not None:
            bot.say('Current quest active: {0.NAME} - {0.OBJECTIVE}'.format(self.current_quest))
        else:
            bot.say('There is no quest active right now.')

    def load_commands(self, **options):
        self.commands['myprogress'] = Command.raw_command(self.my_progress)
        self.commands['currentquest'] = Command.raw_command(self.get_current_quest)

    def on_stream_start(self):
        if len(self.submodules) == 0:
            log.error('No quests enabled.')
            return False

        redis = RedisManager.get()

        self.current_quest = random.choice(self.submodules)
        self.current_quest.start_quest()

        redis.set(self.current_quest_key, self.current_quest.ID)

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

    def on_loaded(self):
        if self.bot:
            self.current_quest_key = '{streamer}:current_quest'.format(streamer=self.bot.streamer)

            if self.current_quest is None:
                redis = RedisManager.get()

                current_quest_id = redis.get(self.current_quest_key)

                log.info('Try to load submodule with ID {}'.format(current_quest_id))

                if current_quest_id is not None:
                    current_quest_id = current_quest_id.decode('utf8')
                    quest = find(lambda m: m.ID == current_quest_id, self.submodules)

                    if quest is not None:
                        log.info('Resumed quest {}'.format(quest.OBJECTIVE))
                        self.current_quest = quest
                        self.current_quest.start_quest()
                    else:
                        log.info('No quest with id {} found in submodules ({})'.format(current_quest_id, self.submodules))
                else:
                    # Fake a stream start to try to randomize a quest
                    self.on_stream_start()

    def disable(self, bot):
        HandlerManager.remove_handler('on_stream_start', self.on_stream_start)
        HandlerManager.remove_handler('on_stream_stop', self.on_stream_stop)

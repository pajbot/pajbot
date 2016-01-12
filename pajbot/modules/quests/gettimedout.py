import logging

from pajbot.modules import BaseModule, ModuleSetting
from pajbot.modules import QuestModule
from pajbot.models.command import Command

log = logging.getLogger(__name__)

class GetTimedOutQuestModule(BaseModule):

    ID = __name__.split('.')[-1]
    NAME = 'Quest'
    DESCRIPTION = 'Get timed out by someone'
    PARENT_MODULE = QuestModule
    SETTINGS = [
            ModuleSetting(
                key='who',
                label='Who did it?',
                type='text',
                required=True,
                placeholder='asdasd',
                default='reddit',
                constraints={
                    'min_str_len': 2,
                    'max_str_len': 15,
                    })
            ]

    def dummy_command(self, **options):
        log.info('asd')
        log.info(options)
        bot = options.get('bot', None)
        if bot:
            bot.say('we did it {}!'.format(self.settings['who']))

    def load_commands(self, **options):
        self.commands['dummy'] = Command.raw_command(self.dummy_command)

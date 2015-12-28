import logging

from pajbot.modules import BaseModule
from pajbot.models.command import Command

log = logging.getLogger(__name__)

class DummyModule(BaseModule):

    ID = __name__.split('.')[-1]
    NAME = 'Dummy module'
    DESCRIPTION = 'This does not actually do anything'

    def dummy_command(self, **options):
        log.info('asd')
        log.info(options)
        bot = options.get('bot', None)
        if bot:
            bot.say('we did it reddit!')

    def load_commands(self, **options):
        self.commands['dummy'] = Command.raw_command(self.dummy_command)

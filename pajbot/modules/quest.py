import logging

from pajbot.modules import BaseModule, ModuleSetting
from pajbot.models.command import Command

log = logging.getLogger(__name__)

class QuestModule(BaseModule):

    ID = __name__.split('.')[-1]
    NAME = 'Quest system'
    DESCRIPTION = 'Give users a single quest at the start of each day'
    SETTINGS = [
            ]

    def load_commands(self, **options):
        # TODO: Add !currentquest command
        pass

    # TODO: Add handlers for on_stream_start and on_stream_stop

    def on_stream_start(self):
        pass

    def enable(self, bot):
        if bot:
            bot.add_handler('on_stream_start', self.on_stream_start)

            # Do we need self.bot?
            self.bot = bot

    def disable(self, bot):
        if bot:
            bot.remove_handler('on_stream_start', self.on_stream_start)

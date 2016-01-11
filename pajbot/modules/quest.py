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

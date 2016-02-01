import logging

from pajbot.modules import BaseModule, ModuleSetting
from pajbot.streamhelper import StreamHelper

log = logging.getLogger(__name__)

class BaseQuest(BaseModule):
    OBJECTIVE = 'No objective set.'

    def __init__(self):
        super().__init__()
        self.progress_key = '{streamer}:current_quest_progress'.format(streamer=StreamHelper.get_streamer())

    def start_quest(self):
        """ This method is triggered by either the stream starting, or the bot loading up
        while a quest/stream is already active """
        log.error('No start quest implemented for this quest.')

    def stop_quest(self):
        """ This method is ONLY called when the stream is stopped. """
        log.error('No stop quest implemented for this quest.')

    def get_objective(self):
        return self.OBJECTIVE

import logging

from pajbot.modules import BaseModule, ModuleSetting

log = logging.getLogger(__name__)

class BaseQuest(BaseModule):
    OBJECTIVE = 'No objective set.'

    def start_quest(self):
        log.error('No start quest implemented for this quest.')

    def stop_quest(self):
        log.error('No stop quest implemented for this quest.')

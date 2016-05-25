import logging

from pajbot.managers.handler import HandlerManager
from pajbot.modules import QuestModule
from pajbot.modules.quests import BaseQuest

log = logging.getLogger(__name__)


class GetTimedOutQuestModule(BaseQuest):

    ID = 'quest-' + __name__.split('.')[-1]
    NAME = 'Quest'
    DESCRIPTION = 'Get timed out by someone'
    PARENT_MODULE = QuestModule
    OBJECTIVE = 'Get timed out by another user'

    def on_paid_timeout(self, source, victim, cost):
        log.warn('{} just timed out {} for {} points'.format(source, victim, cost))

    def enable(self, bot):
        HandlerManager.add_handler('on_paid_timeout', self.on_paid_timeout)

    def disable(self, bot):
        HandlerManager.remove_handler('on_paid_timeout', self.on_paid_timeout)

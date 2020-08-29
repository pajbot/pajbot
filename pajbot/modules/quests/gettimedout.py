import logging

from pajbot.managers.handler import HandlerManager
from pajbot.modules.quest import QuestModule
from pajbot.modules.quests import BaseQuest

log = logging.getLogger(__name__)


class GetTimedOutQuestModule(BaseQuest):

    ID = "quest-" + __name__.split(".")[-1]
    NAME = "Get timed out"
    DESCRIPTION = "Get timed out by someone"
    PARENT_MODULE = QuestModule
    OBJECTIVE = "Get timed out by another user"

    @staticmethod
    def on_paid_timeout(source, victim, cost, **rest):
        log.warning(f"{source} just timed out {victim} for {cost} points")

    def enable(self, bot):
        HandlerManager.add_handler("on_paid_timeout", self.on_paid_timeout)

    def disable(self, bot):
        HandlerManager.remove_handler("on_paid_timeout", self.on_paid_timeout)

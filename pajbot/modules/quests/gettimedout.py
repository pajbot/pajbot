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

    def on_paid_timeout(self, source, victim, cost):
        log.warn('{} just timed out {} for {} points'.format(source, victim, cost))

    def enable(self, bot):
        if bot:
            bot.add_handler('on_paid_timeout', self.on_paid_timeout)

            # Do we need self.bot?
            self.bot = bot

    def disable(self, bot):
        if bot:
            bot.remove_handler('on_paid_timeout', self.on_paid_timeout)

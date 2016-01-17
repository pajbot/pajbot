import logging

from pajbot.modules import BaseModule, ModuleSetting
from pajbot.modules import QuestModule
from pajbot.modules.quests import BaseQuest
from pajbot.models.handler import HandlerManager
from pajbot.models.command import Command

log = logging.getLogger(__name__)

class WinRaffleQuestModule(BaseQuest):

    ID = 'quest-' + __name__.split('.')[-1]
    NAME = 'Win Raffle/Emote Bingo'
    DESCRIPTION = 'A user needs to win a raffle or an emote bingo'
    PARENT_MODULE = QuestModule
    OBJECTIVE = 'win a raffle or an emote bingo'

    def on_paid_timeout(self, source, victim, cost):
        log.warn('{} just timed out {} for {} points'.format(source, victim, cost))

    def on_raffle_win(self, winner, points):
        self.bot.say('{} just won a raffle, he won {} points'.format(
            winner.username_raw, points))

        winner.progress_quest(1)

    def on_bingo_win(self, winner, points, target_emote):
        self.bot.say('{} just won a bingo, he won {} points with the emote {}'.format(
            winner.username_raw, points, target_emote))

        winner.progress_quest(1)

    def start_quest(self):
        HandlerManager.add_handler('on_raffle_win', self.on_raffle_win)
        HandlerManager.add_handler('on_bingo_win', self.on_bingo_win)

    def stop_quest(self):
        HandlerManager.remove_handler('on_raffle_win', self.on_raffle_win)
        HandlerManager.remove_handler('on_bingo_win', self.on_bingo_win)

    def enable(self, bot):
        self.bot = bot

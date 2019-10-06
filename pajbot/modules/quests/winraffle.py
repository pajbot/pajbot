import logging

from pajbot.managers.handler import HandlerManager
from pajbot.managers.redis import RedisManager
from pajbot.modules.quest import QuestModule
from pajbot.modules.quests import BaseQuest

log = logging.getLogger(__name__)


class WinRaffleQuestModule(BaseQuest):

    ID = "quest-" + __name__.split(".")[-1]
    NAME = "Win Raffle/Emote Bingo"
    DESCRIPTION = "A user needs to win a raffle or an emote bingo"
    PARENT_MODULE = QuestModule
    OBJECTIVE = "win a raffle or an emote bingo"

    LIMIT = 1

    @staticmethod
    def on_paid_timeout(source, victim, cost):
        log.warning(f"{source} just timed out {victim} for {cost} points")

    def winraffle_progress_quest(self, winner):
        user_progress = self.get_user_progress(winner, 0) + 1
        if user_progress > 1:
            # User has already finished this quest
            return

        redis = RedisManager.get()

        self.finish_quest(redis, winner)

        self.set_user_progress(winner, user_progress, redis=redis)

    def on_raffle_win(self, winner, **rest):
        self.winraffle_progress_quest(winner)

    def on_bingo_win(self, winner, **rest):
        self.winraffle_progress_quest(winner)

    def on_multiraffle_win(self, winners, points_per_user, **rest):
        for winner in winners:
            self.on_raffle_win(winner)

    def start_quest(self):
        HandlerManager.add_handler("on_raffle_win", self.on_raffle_win)
        HandlerManager.add_handler("on_bingo_win", self.on_bingo_win)
        HandlerManager.add_handler("on_multiraffle_win", self.on_multiraffle_win)

        self.load_progress()

    def stop_quest(self):
        HandlerManager.remove_handler("on_raffle_win", self.on_raffle_win)
        HandlerManager.remove_handler("on_bingo_win", self.on_bingo_win)
        HandlerManager.remove_handler("on_multiraffle_win", self.on_multiraffle_win)

        self.reset_progress()

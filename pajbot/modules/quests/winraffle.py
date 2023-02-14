from typing import List

import logging

from pajbot.managers.handler import HandlerManager
from pajbot.models.user import User
from pajbot.modules.quest import QuestModule
from pajbot.modules.quests.base import BaseQuest

log = logging.getLogger(__name__)


class WinRaffleQuestModule(BaseQuest):
    ID = "quest-" + __name__.split(".")[-1]
    NAME = "Win Raffle/Emote Bingo"
    DESCRIPTION = "A user needs to win a raffle or an emote bingo"
    PARENT_MODULE = QuestModule
    OBJECTIVE = "win a raffle or an emote bingo"

    def winraffle_progress_quest(self, winner: User) -> None:
        user_progress = self.get_user_progress(winner, 0) + 1
        if user_progress > 1:
            # User has already finished this quest
            return

        self.finish_quest(winner)

        self.set_user_progress(winner, user_progress)

    def on_raffle_win(self, winner: User, **rest) -> bool:
        self.winraffle_progress_quest(winner)

        return True

    def on_bingo_win(self, winner: User, **rest) -> bool:
        self.winraffle_progress_quest(winner)

        return True

    def on_multiraffle_win(self, winners: List[User], points_per_user: int, **rest) -> bool:
        for winner in winners:
            self.on_raffle_win(winner)

        return True

    def start_quest(self) -> None:
        HandlerManager.add_handler("on_raffle_win", self.on_raffle_win)
        HandlerManager.add_handler("on_bingo_win", self.on_bingo_win)
        HandlerManager.add_handler("on_multiraffle_win", self.on_multiraffle_win)

        self.load_progress()

    def stop_quest(self) -> None:
        HandlerManager.remove_handler("on_raffle_win", self.on_raffle_win)
        HandlerManager.remove_handler("on_bingo_win", self.on_bingo_win)
        HandlerManager.remove_handler("on_multiraffle_win", self.on_multiraffle_win)

        self.reset_progress()

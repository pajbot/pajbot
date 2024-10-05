import logging

from pajbot.managers.handler import HandlerManager
from pajbot.models.user import User
from pajbot.modules.base import ModuleSetting
from pajbot.modules.quest import QuestModule
from pajbot.modules.quests.base import BaseQuest

log = logging.getLogger(__name__)


class WinDuelsQuestModule(BaseQuest):
    ID = "quest-" + __name__.split(".")[-1]
    NAME = "Win duels"
    DESCRIPTION = "Win X duels and make profit in every duel."
    PARENT_MODULE = QuestModule
    CATEGORY = "Quest"
    SETTINGS = [
        ModuleSetting(
            key="quest_limit",
            label="How many duels must a user win.",
            type="number",
            required=True,
            placeholder="",
            default=10,
            constraints={"min_value": 1, "max_value": 200},
        )
    ]

    def get_limit(self) -> int:
        return self.settings["quest_limit"]

    def on_duel_complete(self, winner: User, points_won: int, **rest) -> bool:
        if points_won < 1:
            return True

        user_progress = self.get_user_progress(winner, default=0)
        if user_progress >= self.get_limit():
            return True

        user_progress += 1

        if user_progress == self.get_limit():
            self.finish_quest(winner)

        self.set_user_progress(winner, user_progress)

        return True

    def start_quest(self) -> None:
        HandlerManager.add_handler("on_duel_complete", self.on_duel_complete)

        self.load_progress()

    def stop_quest(self) -> None:
        HandlerManager.remove_handler("on_duel_complete", self.on_duel_complete)

        self.reset_progress()

    def get_objective(self) -> str:
        return f"Win {self.get_limit()} duels and make profit in every duel."

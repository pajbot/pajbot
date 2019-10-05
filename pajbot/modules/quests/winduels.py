import logging

from pajbot.managers.handler import HandlerManager
from pajbot.managers.redis import RedisManager
from pajbot.modules.base import ModuleSetting
from pajbot.modules.quest import QuestModule
from pajbot.modules.quests import BaseQuest

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

    def get_limit(self):
        return self.settings["quest_limit"]

    def on_duel_complete(self, winner, points_won, **rest):
        if points_won < 1:
            return

        user_progress = self.get_user_progress(winner, default=0)
        if user_progress >= self.get_limit():
            return

        user_progress += 1

        redis = RedisManager.get()

        if user_progress == self.get_limit():
            self.finish_quest(redis, winner)

        self.set_user_progress(winner, user_progress, redis=redis)

    def start_quest(self):
        HandlerManager.add_handler("on_duel_complete", self.on_duel_complete)

        redis = RedisManager.get()

        self.load_progress(redis=redis)

    def stop_quest(self):
        HandlerManager.remove_handler("on_duel_complete", self.on_duel_complete)

        redis = RedisManager.get()

        self.reset_progress(redis=redis)

    def get_objective(self):
        return f"Win {self.get_limit()} duels and make profit in every duel."

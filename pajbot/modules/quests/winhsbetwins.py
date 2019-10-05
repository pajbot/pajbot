import logging

from pajbot.managers.handler import HandlerManager
from pajbot.managers.redis import RedisManager
from pajbot.modules.base import ModuleSetting
from pajbot.modules.quest import QuestModule
from pajbot.modules.quests import BaseQuest

log = logging.getLogger(__name__)


class WinHsBetWinsQuestModule(BaseQuest):

    ID = "quest-" + __name__.split(".")[-1]
    NAME = "HsBet Wins"
    DESCRIPTION = "Bet the right outcome on Hearthstone games X times."
    PARENT_MODULE = QuestModule
    CATEGORY = "Quest"
    SETTINGS = [
        ModuleSetting(
            key="quest_limit",
            label="How many right outcomes must have a user.",
            type="number",
            required=True,
            placeholder="",
            default=4,
            constraints={"min_value": 1, "max_value": 20},
        )
    ]

    def get_limit(self):
        return self.settings["quest_limit"]

    def on_user_win_hs_bet(self, user, **rest):
        # User needs to make 1 point profit at least
        # if points_reward < 1:
        #    return

        user_progress = self.get_user_progress(user, default=0)
        if user_progress >= self.get_limit():
            return

        user_progress += 1

        redis = RedisManager.get()

        if user_progress == self.get_limit():
            self.finish_quest(redis, user)

        self.set_user_progress(user, user_progress, redis=redis)

    def start_quest(self):
        HandlerManager.add_handler("on_user_win_hs_bet", self.on_user_win_hs_bet)

        redis = RedisManager.get()

        self.load_progress(redis=redis)

    def stop_quest(self):
        HandlerManager.remove_handler("on_user_win_hs_bet", self.on_user_win_hs_bet)

        redis = RedisManager.get()

        self.reset_progress(redis=redis)

    def get_objective(self):
        return f"Bet the right outcome on {self.get_limit()} Hearthstone games."

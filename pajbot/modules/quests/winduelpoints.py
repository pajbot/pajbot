import logging
import random

from pajbot.managers.handler import HandlerManager
from pajbot.managers.redis import RedisManager
from pajbot.modules.base import ModuleSetting
from pajbot.modules.quest import QuestModule
from pajbot.modules.quests import BaseQuest
from pajbot.streamhelper import StreamHelper

log = logging.getLogger(__name__)


class WinDuelPointsQuestModule(BaseQuest):

    ID = "quest-" + __name__.split(".")[-1]
    NAME = "Win points in duels"
    DESCRIPTION = "You need to win X amount of points in a duel to complete this quest."
    PARENT_MODULE = QuestModule
    SETTINGS = [
        ModuleSetting(
            key="min_value",
            label="Minimum amount of points the user needs to win",
            type="number",
            required=True,
            placeholder="",
            default=250,
            constraints={"min_value": 50, "max_value": 2000},
        ),
        ModuleSetting(
            key="max_value",
            label="Maximum amount of points the user needs to win",
            type="number",
            required=True,
            placeholder="",
            default=750,
            constraints={"min_value": 100, "max_value": 4000},
        ),
    ]

    LIMIT = 1

    def __init__(self, bot):
        super().__init__(bot)
        self.points_required_key = f"{StreamHelper.get_streamer()}:current_quest_points_required"
        # The points_required variable is randomized at the start of the quest.
        # It will be a value between settings['min_value'] and settings['max_value']
        self.points_required = None
        self.progress = {}

    def on_duel_complete(self, winner, points_won, **rest):
        if points_won < 1:
            # This duel did not award any points.
            # That means it's entirely irrelevant to us
            return

        total_points_won = self.get_user_progress(winner, default=0)
        if total_points_won >= self.points_required:
            # The user has already won enough points, and been rewarded already.
            return

        # If we get here, this means the user has not completed the quest yet.
        # And the user won some points in this duel
        total_points_won += points_won

        redis = RedisManager.get()

        if total_points_won >= self.points_required:
            # Reward the user with some tokens
            self.finish_quest(redis, winner)

        # Save the users "points won" progress
        self.set_user_progress(winner, total_points_won, redis=redis)

    def start_quest(self):
        HandlerManager.add_handler("on_duel_complete", self.on_duel_complete)

        redis = RedisManager.get()

        self.load_progress(redis=redis)
        self.load_data(redis=redis)

        self.LIMIT = self.points_required

    def load_data(self, redis=None):
        if redis is None:
            redis = RedisManager.get()

        self.points_required = redis.get(self.points_required_key)
        try:
            self.points_required = int(self.points_required)
        except (TypeError, ValueError):
            pass
        if self.points_required is None:
            try:
                self.points_required = random.randint(self.settings["min_value"], self.settings["max_value"])
            except ValueError:
                # someone fucked up
                self.points_required = 500
            redis.set(self.points_required_key, self.points_required)

    def stop_quest(self):
        HandlerManager.remove_handler("on_duel_complete", self.on_duel_complete)

        redis = RedisManager.get()

        self.reset_progress(redis=redis)
        redis.delete(self.points_required_key)

    def get_objective(self):
        return f"Make a profit of {self.points_required} or more points in one or multiple duels."

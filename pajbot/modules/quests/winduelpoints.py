from __future__ import annotations

from typing import TYPE_CHECKING, Optional

import logging
import random

from pajbot.managers.handler import HandlerManager
from pajbot.managers.redis import RedisManager
from pajbot.models.user import User
from pajbot.modules.base import ModuleSetting
from pajbot.modules.quest import QuestModule
from pajbot.modules.quests.base import BaseQuest
from pajbot.streamhelper import StreamHelper

if TYPE_CHECKING:
    from pajbot.bot import Bot

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

    def __init__(self, bot: Optional[Bot]) -> None:
        super().__init__(bot)
        self.points_required_key = f"{StreamHelper.get_streamer()}:current_quest_points_required"
        # The points_required variable is randomized at the start of the quest.
        # It will be a value between settings['min_value'] and settings['max_value']
        self.points_required: Optional[int] = None

    def on_duel_complete(self, winner: User, points_won: int, **rest) -> bool:
        if points_won < 1:
            # This duel did not award any points.
            # That means it's entirely irrelevant to us
            return True

        if self.points_required is None:
            # This duel happened before the quest was initialized
            return True

        total_points_won = self.get_user_progress(winner, default=0)
        if total_points_won >= self.points_required:
            # The user has already won enough points, and been rewarded already.
            return True

        # If we get here, this means the user has not completed the quest yet.
        # And the user won some points in this duel
        total_points_won += points_won

        if total_points_won >= self.points_required:
            # Reward the user with some tokens
            self.finish_quest(winner)

        # Save the users "points won" progress
        self.set_user_progress(winner, total_points_won)

        return True

    def start_quest(self) -> None:
        HandlerManager.add_handler("on_duel_complete", self.on_duel_complete)

        self.load_progress()
        self.load_data()

    def load_data(self) -> None:
        redis = RedisManager.get()

        self.points_required = None
        points_required = redis.get(self.points_required_key)
        try:
            if points_required:
                self.points_required = int(points_required)
        except (TypeError, ValueError):
            pass

        if self.points_required is None:
            try:
                self.points_required = random.randint(self.settings["min_value"], self.settings["max_value"])
            except ValueError:
                # someone fucked up
                self.points_required = 500
            redis.set(self.points_required_key, self.points_required)

    def stop_quest(self) -> None:
        HandlerManager.remove_handler("on_duel_complete", self.on_duel_complete)

        redis = RedisManager.get()

        self.reset_progress()
        redis.delete(self.points_required_key)

    def get_objective(self) -> str:
        return f"Make a profit of {self.points_required} or more points in one or multiple duels."

    def get_limit(self) -> int:
        if self.points_required is None:
            log.warn("Get limit called in WinDuelPoints before quest is initialized")
            return 1

        return self.points_required

from __future__ import annotations

from typing import TYPE_CHECKING, Dict, Optional, final

import json
import logging

from pajbot.managers.redis import RedisManager
from pajbot.models.user import User
from pajbot.modules.base import BaseModule
from pajbot.streamhelper import StreamHelper

if TYPE_CHECKING:
    from pajbot.bot import Bot
    from pajbot.modules.quest import QuestModule

log = logging.getLogger(__name__)


class BaseQuest(BaseModule):
    OBJECTIVE = "No objective set."

    def __init__(self, bot: Optional[Bot]) -> None:
        super().__init__(bot)
        self.progress: Dict[str, int] = {}
        self.progress_key = f"{StreamHelper.get_streamer()}:current_quest_progress"
        self.quest_finished_key = f"{StreamHelper.get_streamer()}:quests:finished"
        self.quest_module: Optional[QuestModule] = None

    def finish_quest(self, user: User) -> None:
        if not self.quest_module:
            log.error("Quest module not initialized")
            return

        if self.bot is None:
            log.warning("Module bot is None")
            return

        redis = RedisManager.get()

        stream_id = StreamHelper.get_current_stream_id()

        # Load user's finished quest status
        val = redis.hget(self.quest_finished_key, user.id)
        if val:
            quests_finished = json.loads(val)
        else:
            quests_finished = []

        if stream_id in quests_finished:
            # User has already completed this quest
            return

        reward_type = self.quest_module.settings["reward_type"]
        reward_amount = self.quest_module.settings["reward_amount"]

        if reward_type == "tokens" and user.tokens > self.quest_module.settings["max_tokens"]:
            message = (
                "You finished todays quest, but you have more than the max tokens allowed already. Spend some tokens!"
            )
            self.bot.whisper(user, message)
            return

        # Mark the current stream ID has finished
        quests_finished.append(stream_id)
        redis.hset(self.quest_finished_key, user.id, json.dumps(quests_finished, separators=(",", ":")))

        # Award the user appropriately
        if reward_type == "tokens":
            user.tokens += reward_amount
        else:
            user.points += reward_amount

        # Notify the user that they've finished today's quest
        message = f"You finished todays quest! You have been awarded with {reward_amount} {reward_type}."
        self.bot.whisper(user, message)

    def start_quest(self) -> None:
        """This method is triggered by either the stream starting, or the bot loading up
        while a quest/stream is already active"""
        log.error("No start quest implemented for this quest.")

    def stop_quest(self) -> None:
        """This method is ONLY called when the stream is stopped."""
        log.error("No stop quest implemented for this quest.")

    @final
    def get_user_progress(self, user: User, default: int = 0) -> int:
        return self.progress.get(user.id, default)

    @final
    def set_user_progress(self, user: User, new_progress: int) -> None:
        redis = RedisManager.get()

        redis.hset(self.progress_key, user.id, new_progress)
        self.progress[user.id] = new_progress

    def load_progress(self) -> None:
        """Reset & load progress from Redis
        Used when a quest is already started and the bot restarts"""
        redis = RedisManager.get()

        self.progress = {}
        old_progress = redis.hgetall(self.progress_key)
        for user_id, progress in old_progress.items():
            try:
                self.progress[user_id] = int(progress)
            except (TypeError, ValueError):
                pass

    def load_data(self) -> None:
        """
        Useful base method for loading dynamic parts of the quest.
        For example, what emote is supposed to be used in the type emote quest
        """

    def reset_progress(self) -> None:
        redis = RedisManager.get()

        redis.delete(self.progress_key)

    def get_objective(self) -> str:
        return self.OBJECTIVE

    def get_limit(self) -> int:
        """Returns the quest limit specified in the module.
        If no quest limit is set by the module, return 1.
        A value of 1 would indicate a quest that only has an incomplete/complete state."""

        return 1

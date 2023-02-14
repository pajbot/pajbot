from __future__ import annotations

from typing import TYPE_CHECKING, List, Optional

import json
import logging

from pajbot.managers.handler import HandlerManager
from pajbot.managers.redis import RedisManager
from pajbot.models.emote import Emote, EmoteInstance
from pajbot.models.user import User
from pajbot.modules.base import ModuleSetting
from pajbot.modules.quest import QuestModule
from pajbot.modules.quests.base import BaseQuest
from pajbot.streamhelper import StreamHelper

if TYPE_CHECKING:
    from pajbot.bot import Bot

log = logging.getLogger(__name__)


class TypeEmoteQuestModule(BaseQuest):
    ID = "quest-" + __name__.split(".")[-1]
    NAME = "Type X emote Y times"
    DESCRIPTION = "A user needs to type a specific emote Y times to complete this quest."
    PARENT_MODULE = QuestModule
    SETTINGS = [
        ModuleSetting(
            key="quest_limit",
            label="How many emotes you need to type",
            type="number",
            required=True,
            placeholder="How many emotes you need to type (default 100)",
            default=100,
            constraints={"min_value": 10, "max_value": 200},
        )
    ]

    def __init__(self, bot: Optional[Bot]) -> None:
        super().__init__(bot)
        self.current_emote_key = f"{StreamHelper.get_streamer()}:current_quest_emote"
        self.current_emote: Optional[Emote] = None

    def get_limit(self) -> int:
        return self.settings["quest_limit"]

    def on_message(self, source: User, emote_instances: List[EmoteInstance], **rest) -> bool:
        typed_emotes = {emote_instance.emote for emote_instance in emote_instances}
        if self.current_emote not in typed_emotes:
            return True

        user_progress = self.get_user_progress(source, default=0) + 1

        if user_progress > self.get_limit():
            log.debug(f"{source} has already completed the quest. Moving along.")
            # no need to do more
            return True

        if user_progress == self.get_limit():
            self.finish_quest(source)

        self.set_user_progress(source, user_progress)

        return True

    def start_quest(self) -> None:
        HandlerManager.add_handler("on_message", self.on_message)

        self.load_progress()
        self.load_data()

    def load_data(self) -> None:
        assert self.bot is not None

        redis = RedisManager.get()

        redis_json = redis.get(self.current_emote_key)
        if redis_json is None:
            # randomize an emote
            # TODO possibly a setting to allow the user to configure the twitch_global=True, etc
            #      parameters to random_emote?
            self.current_emote = self.bot.emote_manager.random_emote(twitch_global=True)
            # If EmoteManager has no global emotes, current_emote will be None
            if self.current_emote is not None:
                redis.set(self.current_emote_key, json.dumps(self.current_emote.jsonify()))
        else:
            self.current_emote = Emote(**json.loads(redis_json))

    def stop_quest(self) -> None:
        HandlerManager.remove_handler("on_message", self.on_message)

        redis = RedisManager.get()

        self.reset_progress()
        redis.delete(self.current_emote_key)

    def get_objective(self) -> str:
        if not self.current_emote:
            return "No emote chosen, quest not initialized"

        return f"Use the {self.current_emote.code} emote {self.get_limit()} times"

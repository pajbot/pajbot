import logging

import json

from pajbot.managers.handler import HandlerManager
from pajbot.managers.redis import RedisManager
from pajbot.models.emote import Emote
from pajbot.modules.base import ModuleSetting
from pajbot.modules.quest import QuestModule
from pajbot.modules.quests import BaseQuest
from pajbot.streamhelper import StreamHelper

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

    def __init__(self, bot):
        super().__init__(bot)
        self.current_emote_key = f"{StreamHelper.get_streamer()}:current_quest_emote"
        self.current_emote = None
        self.progress = {}

    def get_limit(self):
        return self.settings["quest_limit"]

    def on_message(self, source, emote_instances, **rest):
        typed_emotes = {emote_instance.emote for emote_instance in emote_instances}
        if self.current_emote not in typed_emotes:
            return

        user_progress = self.get_user_progress(source, default=0) + 1

        if user_progress > self.get_limit():
            log.debug(f"{source} has already completed the quest. Moving along.")
            # no need to do more
            return

        redis = RedisManager.get()

        if user_progress == self.get_limit():
            self.finish_quest(redis, source)

        self.set_user_progress(source, user_progress, redis=redis)

    def start_quest(self):
        HandlerManager.add_handler("on_message", self.on_message)

        redis = RedisManager.get()

        self.load_progress(redis=redis)
        self.load_data(redis=redis)

    def load_data(self, redis=None):
        if redis is None:
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

    def stop_quest(self):
        HandlerManager.remove_handler("on_message", self.on_message)

        redis = RedisManager.get()

        self.reset_progress(redis=redis)
        redis.delete(self.current_emote_key)

    def get_objective(self):
        return f"Use the {self.current_emote.code} emote {self.get_limit()} times"

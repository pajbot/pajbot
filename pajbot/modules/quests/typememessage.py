from typing import Any

import logging

from pajbot.managers.handler import HandlerManager
from pajbot.models.user import User
from pajbot.modules.base import ModuleSetting
from pajbot.modules.quest import QuestModule
from pajbot.modules.quests.base import BaseQuest

log = logging.getLogger(__name__)


class TypeMeMessageQuestModule(BaseQuest):
    ID = "quest-" + __name__.split(".")[-1]
    NAME = "Colorful chat /me"
    DESCRIPTION = "Type X /me messages with X message length."
    PARENT_MODULE = QuestModule
    CATEGORY = "Quest"
    SETTINGS = [
        ModuleSetting(
            key="quest_limit",
            label="How many messages does the user needs to type?",
            type="number",
            required=True,
            placeholder="",
            default=100,
            constraints={"min_value": 1, "max_value": 200},
        ),
        ModuleSetting(
            key="quest_message_length",
            label="How many letters minimum should be in the message?",
            type="number",
            required=True,
            placeholder="",
            default=15,
            constraints={"min_value": 1, "max_value": 500},
        ),
    ]

    def get_limit(self) -> int:
        return self.settings["quest_limit"]

    def get_quest_message_length(self) -> int:
        return self.settings["quest_message_length"]

    def on_message(self, source: User, message: str, event: Any, **rest) -> bool:
        if len(message) < self.get_quest_message_length() or event.type != "action":
            return True

        user_progress = self.get_user_progress(source, default=0)

        if user_progress >= self.get_limit():
            return True

        user_progress += 1

        if user_progress == self.get_limit():
            self.finish_quest(source)

        self.set_user_progress(source, user_progress)

        return True

    def start_quest(self) -> None:
        HandlerManager.add_handler("on_message", self.on_message)

        self.load_progress()

    def stop_quest(self) -> None:
        HandlerManager.remove_handler("on_message", self.on_message)

        self.reset_progress()

    def get_objective(self) -> str:
        return f"Type {self.get_limit()} /me messages with a length of minimum {self.get_quest_message_length()} letters KappaPride "

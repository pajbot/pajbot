import logging

from pajbot.managers.handler import HandlerManager
from pajbot.managers.db import DBManager
from pajbot.modules import BaseModule
from pajbot.modules import ModuleSetting
from pajbot.models.user import User

log = logging.getLogger(__name__)


class ConvertPoints(BaseModule):
    ID = __name__.split(".")[-1]
    NAME = "Convert Points"
    DESCRIPTION = "Convert channel points to bot points"
    CATEGORY = "Feature"
    SETTINGS = [
        ModuleSetting(
            key="redeemed_id",
            label="ID of redemeed prize",
            type="text",
            required=True,
            default="",
            constraints={"min_str_len": 36, "max_str_len": 36},
        ),
        ModuleSetting(key="points", label="Number of points", type="number", required=True, default=10000),
    ]

    def on_redeem(self, redeemer, redeemed_id, user_input):
        if user_input is not None and redeemed_id == self.settings["redeemed_id"]:
            with DBManager.create_session_scope() as db_session:
                user = User.from_basics(db_session, redeemer)
                user.points += self.settings["points"]
                self.bot.whisper(user, f"You have been given {self.settings['points']}")

    def enable(self, bot):
        if not bot:
            return

        HandlerManager.add_handler("on_redeem", self.on_redeem)

    def disable(self, bot):
        if not bot:
            return

        HandlerManager.remove_handler("on_redeem", self.on_redeem)

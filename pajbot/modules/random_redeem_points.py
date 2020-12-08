import logging
import random

from pajbot.managers.handler import HandlerManager
from pajbot.managers.db import DBManager
from pajbot.modules import BaseModule
from pajbot.modules import ModuleSetting
from pajbot.models.user import User

log = logging.getLogger(__name__)


class RandomRedeem(BaseModule):
    ID = __name__.split(".")[-1]
    NAME = "Random Redeems"
    DESCRIPTION = "Gives a random number of points when they redeem a reward"
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
        ModuleSetting(
            key="lower_points", label="Lower bound number of points", type="number", required=True, default=10000
        ),
        ModuleSetting(
            key="upper_points", label="Upper bound number of points", type="number", required=True, default=10000
        ),
    ]

    def on_redeem(self, redeemer, redeemed_id, user_input):
        if user_input is not None and redeemed_id == self.settings["redeemed_id"]:
            with DBManager.create_session_scope() as db_session:
                user = User.from_basics(db_session, redeemer)
                points = random.randint(self.settings["lower_points"], self.settings["upper_points"])
                user.points += points
                self.bot.whisper(user, f"You have been given {points}")

    def enable(self, bot):
        if not bot:
            return

        HandlerManager.add_handler("on_redeem", self.on_redeem)

    def disable(self, bot):
        if not bot:
            return

        HandlerManager.remove_handler("on_redeem", self.on_redeem)

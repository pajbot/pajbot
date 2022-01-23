import logging

from pajbot.managers.db import DBManager
from pajbot.models.command import Command, CommandExample
from pajbot.models.user import User
from pajbot.modules import BaseModule
from pajbot.modules.basic import BasicCommandsModule

log = logging.getLogger(__name__)


class PointsResetModule(BaseModule):

    ID = __name__.split(".")[-1]
    NAME = "Points Reset"
    DESCRIPTION = "Reset points from a user with negative points."
    CATEGORY = "Feature"
    PARENT_MODULE = BasicCommandsModule

    @staticmethod
    def points_reset(bot, source, message, **options):
        if message is None or len(message) == 0:
            return

        username = message.split(" ")[0]
        if len(username) < 2:
            return

        with DBManager.create_session_scope() as db_session:
            victim = User.find_by_user_input(db_session, username)
            if victim is None:
                bot.whisper(source, "This user does not exist FailFish")
                return

            if victim.points >= 0:
                bot.whisper(source, f"{victim} doesn't have negative points FailFish")
                return

            if victim.points <= -1:
                old_points = victim.points
                victim.points = 0
                bot.whisper(source, f"You changed the points for {victim} from {old_points} to {victim.points} points")

    def load_commands(self, **options):
        self.commands["pointsreset"] = Command.raw_command(
            self.points_reset,
            delay_all=0,
            delay_user=5,
            level=500,
            description="Reset points from a user with negative points.",
            can_execute_with_whisper=1,
            command="pointsreset",
            examples=[
                CommandExample(
                    None,
                    "Reset points from a user with negative points.",
                    chat="user:!pointsreset pajtest\n"
                    "bot>user:You changed the points for pajtest from -10000 to 0 points",
                    description="",
                ).parse()
            ],
        )

import logging

from pajbot.models.command import Command
from pajbot.models.command import CommandExample
from pajbot.modules import BaseModule
from pajbot.modules.basic import BasicCommandsModule

log = logging.getLogger(__name__)


class PointsResetModule(BaseModule):

    ID = __name__.split(".")[-1]
    NAME = "!pointsreset"
    DESCRIPTION = "Reset points from a user with negative points."
    CATEGORY = "Feature"
    PARENT_MODULE = BasicCommandsModule

    @staticmethod
    def points_reset(**options):
        message = options["message"]
        bot = options["bot"]
        source = options["source"]

        if message is None or len(message) == 0:
            return

        username = message.split(" ")[0]
        if len(username) < 2:
            return

        with bot.users.find_context(username) as victim:
            if victim is None:
                bot.whisper(source.username, "This user does not exist FailFish")
                return

            if victim.points >= 0:
                bot.whisper(source.username, "{0} doesn't have negative points FailFish".format(victim.username_raw))
                return

            if victim.points <= -1:
                old_points = victim.points
                victim.points = 0
                bot.whisper(
                    source.username,
                    "You changed the points for {0} from {1} to {2} points".format(
                        victim.username_raw, old_points, victim.points
                    ),
                )

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

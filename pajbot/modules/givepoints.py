import logging

from pajbot import utils
from pajbot.exc import InvalidPointAmount
from pajbot.managers.db import DBManager
from pajbot.models.command import Command, CommandExample
from pajbot.models.user import User
from pajbot.modules import BaseModule, ModuleSetting

log = logging.getLogger(__name__)


class GivePointsModule(BaseModule):

    ID = __name__.split(".")[-1]
    NAME = "Give Points"
    DESCRIPTION = "Allows users to donate points to others"
    CATEGORY = "Feature"
    SETTINGS = [
        ModuleSetting(
            key="command_name",
            label="Command name (i.e. givepoints)",
            type="text",
            required=True,
            placeholder="Command name (no !)",
            default="givepoints",
            constraints={"min_str_len": 2, "max_str_len": 25},
        ),
        ModuleSetting(
            key="source_requires_sub",
            label="Users need to be subbed to give away points",
            type="boolean",
            required=True,
            default=True,
        ),
        ModuleSetting(
            key="target_requires_sub",
            label="Target needs to be subbed to receive points",
            type="boolean",
            required=True,
            default=False,
        ),
    ]

    def give_points(self, bot, source, message, **rest):
        if message is None or len(message) == 0:
            # The user did not supply any arguments
            return False

        msg_split = message.split(" ")
        if len(msg_split) < 2:
            # The user did not supply enough arguments
            bot.whisper(source, f"Usage: !{self.command_name} USERNAME POINTS")
            return False

        input = msg_split[0]

        try:
            num_points = utils.parse_points_amount(source, msg_split[1])
        except InvalidPointAmount as e:
            bot.whisper(source, f"{e}. Usage: !{self.command_name} USERNAME POINTS")
            return False

        if num_points <= 0:
            # The user tried to specify a negative amount of points
            bot.whisper(source, "You cannot give away negative points OMGScoots")
            return True

        if not source.can_afford(num_points):
            # The user tried giving away more points than he owns
            bot.whisper(source, f"You cannot give away more points than you have. You have {source.points} points.")
            return False

        with DBManager.create_session_scope() as db_session:
            target = User.find_by_user_input(db_session, input)
            if target is None:
                # The user tried donating points to someone who doesn't exist in our database
                bot.whisper(source, "This user does not exist FailFish")
                return False

            if target == source:
                # The user tried giving points to themselves
                bot.whisper(source, "You can't give points to yourself OMGScoots")
                return True

            if self.settings["target_requires_sub"] is True and target.subscriber is False:
                # Settings indicate that the target must be a subscriber, which he isn't
                bot.whisper(source, "Your target must be a subscriber.")
                return False

            source.points -= num_points
            target.points += num_points

            bot.whisper(source, f"Successfully gave away {num_points} points to {target}")
            bot.whisper(target, f"{source} just gave you {num_points} points! You should probably thank them ;-)")

    def load_commands(self, **options):
        self.command_name = self.settings["command_name"].lower().replace("!", "").replace(" ", "")
        self.commands[self.command_name] = Command.raw_command(
            self.give_points,
            sub_only=self.settings["source_requires_sub"],
            delay_all=0,
            delay_user=60,
            can_execute_with_whisper=True,
            examples=[
                CommandExample(
                    None,
                    "Give points to a user.",
                    chat=f"user:!{self.command_name} pajapaja 4444\n"
                    "bot>user: Successfully gave away 4444 points to pajapaja",
                    description="",
                ).parse()
            ],
        )

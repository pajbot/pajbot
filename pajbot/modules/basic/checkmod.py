import logging

from pajbot.models.command import Command
from pajbot.modules import BaseModule
from pajbot.modules.basic import BasicCommandsModule

log = logging.getLogger(__name__)


class CheckModModule(BaseModule):

    ID = __name__.split(".")[-1]
    NAME = "!checkmod"
    DESCRIPTION = "Checks if a user is marked as a moderator or not"
    CATEGORY = "Feature"
    PARENT_MODULE = BasicCommandsModule

    @staticmethod
    def check_mod(**options):
        message = options["message"]
        bot = options["bot"]
        source = options["source"]

        if message:
            username = message.split(" ")[0].strip().lower()
            user = bot.users.find(username)
        else:
            user = source

        if user:
            if user.moderator:
                bot.say("{0} is a moderator PogChamp".format(user.username_raw))
            else:
                bot.say("{0} is not a moderator FeelsBadMan (or has not typed in chat)".format(user.username_raw))
        else:
            bot.say("{0} was not found in the user database".format(username))

    def load_commands(self, **options):
        self.commands["checkmod"] = Command.raw_command(self.check_mod, level=100, delay_all=3, delay_user=6)

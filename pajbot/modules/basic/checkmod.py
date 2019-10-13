import logging

from pajbot.managers.db import DBManager
from pajbot.models.command import Command
from pajbot.models.user import User
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
    def check_mod(bot, source, message, **rest):
        if message:
            username = message.split(" ")[0]
            with DBManager.create_session_scope(expire_on_commit=False) as db_session:
                user = User.find_by_user_input(db_session, username)

                if user is None:
                    bot.say(f"{username} was not found in the user database")
        else:
            user = source

        if user.moderator:
            bot.say(f"{user} is a moderator PogChamp")
        else:
            bot.say(f"{user} is not a moderator FeelsBadMan (or has not typed in chat) FeelsBadMan")

    def load_commands(self, **options):
        self.commands["checkmod"] = Command.raw_command(self.check_mod, level=100, delay_all=3, delay_user=6)

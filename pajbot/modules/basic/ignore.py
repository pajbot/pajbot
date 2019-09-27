import logging

from pajbot.models.command import Command
from pajbot.models.command import CommandExample
from pajbot.modules import BaseModule
from pajbot.modules import ModuleType
from pajbot.modules.basic import BasicCommandsModule

log = logging.getLogger(__name__)


class IgnoreModule(BaseModule):

    ID = __name__.split(".")[-1]
    NAME = "!ignore/!unignore"
    DESCRIPTION = "Ignore all commands from a user"
    CATEGORY = "Feature"
    ENABLED_DEFAULT = True
    MODULE_TYPE = ModuleType.TYPE_ALWAYS_ENABLED
    PARENT_MODULE = BasicCommandsModule

    @staticmethod
    def ignore_command(**options):
        message = options["message"]
        bot = options["bot"]
        source = options["source"]

        if message:
            username = message.split(" ")[0].strip().lower()

            if username == source.username:
                bot.whisper(source.username, "You cannot ignore yourself")
                return False

            with bot.users.find_context(username) as user:
                if not user:
                    bot.whisper(source.username, "No user with that name found.")
                    return False

                if user.ignored:
                    bot.whisper(source.username, "User is already ignored.")
                    return False

                user.ignored = True
                message = message.lower()
                bot.whisper(source.username, "Now ignoring {0}".format(user.username))

    @staticmethod
    def unignore_command(**options):
        message = options["message"]
        bot = options["bot"]
        source = options["source"]

        if message:
            username = message.split(" ")[0].strip().lower()
            with bot.users.find_context(username) as user:
                if not user:
                    bot.whisper(source.username, "No user with that name found.")
                    return False

                if user.ignored is False:
                    bot.whisper(source.username, "User is not ignored.")
                    return False

                user.ignored = False
                message = message.lower()
                bot.whisper(source.username, "No longer ignoring {0}".format(user.username))

    def load_commands(self, **options):
        self.commands["ignore"] = Command.raw_command(
            self.ignore_command,
            level=1000,
            description="Ignore a user, which means he can't run any commands",
            examples=[
                CommandExample(
                    None,
                    "Default usage",
                    chat="user:!ignore Karl_Kons\n" "bot>user:Now ignoring Karl_Kons",
                    description="Ignore user Karl_Kons",
                ).parse()
            ],
        )

        self.commands["unignore"] = Command.raw_command(
            self.unignore_command,
            level=1000,
            description="Unignore a user",
            examples=[
                CommandExample(
                    None,
                    "Default usage",
                    chat="user:!unignore Karl_Kons\n" "bot>user:No longer ignoring Karl_Kons",
                    description="Unignore user Karl_Kons",
                ).parse()
            ],
        )

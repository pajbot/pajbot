import logging

from pajbot.managers.adminlog import AdminLogManager
from pajbot.models.command import Command
from pajbot.models.command import CommandExample
from pajbot.modules import BaseModule
from pajbot.modules import ModuleType
from pajbot.modules.basic import BasicCommandsModule
from pajbot.utils import split_into_chunks_with_prefix

log = logging.getLogger(__name__)


class AdminCommandsModule(BaseModule):
    ID = __name__.split(".")[-1]
    NAME = "Basic admin commands"
    DESCRIPTION = "All miscellaneous admin commands"
    CATEGORY = "Feature"
    ENABLED_DEFAULT = True
    MODULE_TYPE = ModuleType.TYPE_ALWAYS_ENABLED
    PARENT_MODULE = BasicCommandsModule

    @staticmethod
    def whisper(**options):
        message = options["message"]
        bot = options["bot"]

        if message:
            msg_args = message.split(" ")
            if len(msg_args) > 1:
                username = msg_args[0]
                rest = " ".join(msg_args[1:])
                bot.whisper(username, rest)

    def edit_points(self, **options):
        message = options["message"]
        bot = options["bot"]
        source = options["source"]

        if message:
            msg_split = message.split(" ")
            if len(msg_split) < 2:
                # The user did not supply enough arguments
                bot.whisper(
                    source.username, "Usage: !{command_name} USERNAME POINTS".format(command_name=self.command_name)
                )
                return False

            username = msg_split[0]
            if len(username) < 2:
                # The username specified was too short. ;-)
                return False

            try:
                num_points = int(msg_split[1])
            except (ValueError, TypeError):
                # The user did not specify a valid integer for points
                bot.whisper(
                    source.username,
                    "Invalid amount of points. Usage: !{command_name} USERNAME POINTS".format(
                        command_name=self.command_name
                    ),
                )
                return False

            with bot.users.find_context(username) as user:
                if not user:
                    bot.whisper(source.username, "This user does not exist FailFish")
                    return False

                user.points += num_points

                if num_points >= 0:
                    bot.whisper(
                        source.username, "Successfully gave {} {} points.".format(user.username_raw, num_points)
                    )
                else:
                    bot.whisper(
                        source.username,
                        "Successfully removed {} points from {}.".format(abs(num_points), user.username_raw),
                    )

    def set_points(self, **options):
        message = options["message"]
        bot = options["bot"]
        source = options["source"]

        if message:
            msg_split = message.split(" ")
            if len(msg_split) < 2:
                # The user did not supply enough arguments
                bot.whisper(
                    source.username, "Usage: !{command_name} USERNAME POINTS".format(command_name=self.command_name)
                )
                return False

            username = msg_split[0]
            if len(username) < 2:
                # The username specified was too short. ;-)
                return False

            try:
                num_points = int(msg_split[1])
            except (ValueError, TypeError):
                # The user did not specify a valid integer for points
                bot.whisper(
                    source.username,
                    "Invalid amount of points. Usage: !{command_name} USERNAME POINTS".format(
                        command_name=self.command_name
                    ),
                )
                return False

            with bot.users.find_context(username) as user:
                if not user:
                    bot.whisper(source.username, "This user does not exist FailFish")
                    return False

                user.points = num_points

                bot.whisper(
                    source.username, "Successfully set {}'s points to {}.".format(user.username_raw, num_points)
                )

    @staticmethod
    def level(**options):
        message = options["message"]
        bot = options["bot"]
        source = options["source"]

        if message:
            msg_args = message.split(" ")
            if len(msg_args) > 1:
                username = msg_args[0].lower()
                new_level = int(msg_args[1])
                if new_level >= source.level:
                    bot.whisper(
                        source.username,
                        "You cannot promote someone to the same or higher level as you ({0}).".format(source.level),
                    )
                    return False

                # We create the user if the user didn't already exist in the database.
                with bot.users.get_user_context(username) as user:
                    if user.level >= source.level:
                        bot.whisper(
                            source.username,
                            "You cannot change the level of someone who is the same or higher level than you. You are level {}, and {} is level {}".format(
                                source.level, username, user.level
                            ),
                        )
                        return False

                    old_level = user.level
                    user.level = new_level

                    log_msg = "{}'s user level changed from {} to {}".format(user.username_raw, old_level, new_level)

                    bot.whisper(source.username, log_msg)

                    AdminLogManager.add_entry("Userlevel edited", source, log_msg)

                    return True

        bot.whisper(source.username, "Usage: !level USERNAME NEW_LEVEL")
        return False

    @staticmethod
    def cmd_silence(**options):
        bot = options["bot"]
        source = options["source"]

        if bot.silent:
            bot.whisper(source.username, "The bot is already silent")
        else:
            bot.silent = True
            bot.whisper(
                source.username,
                "The bot is now silent. Use !unsilence to enable messages again. Note that this option does not stick in case the bot crashes or restarts",
            )

    @staticmethod
    def cmd_unsilence(**options):
        bot = options["bot"]
        source = options["source"]

        if not bot.silent:
            bot.whisper(source.username, "The bot can already talk")
        else:
            bot.silent = False
            bot.whisper(source.username, "The bot can now talk again")

    @staticmethod
    def cmd_module(**options):
        bot = options["bot"]
        # source = options['source']
        message = options["message"]

        module_manager = bot.module_manager

        if not message:
            return

        msg_args = message.split(" ")
        if len(msg_args) < 1:
            return

        sub_command = msg_args[0].lower()

        if sub_command == "list":
            messages = split_into_chunks_with_prefix(
                [{"prefix": "Available modules:", "parts": [module.ID for module in module_manager.all_modules]}],
                " ",
                default="No modules available.",
            )

            for message in messages:
                bot.say(message)
        elif sub_command == "disable":
            if len(msg_args) < 2:
                return
            module_id = msg_args[1].lower()

            module = module_manager.get_module(module_id)
            if not module:
                bot.say("No module with the id {} found".format(module_id))
                return

            if module.MODULE_TYPE > ModuleType.TYPE_NORMAL:
                bot.say("Unable to disable module {}".format(module_id))
                return

            if not module_manager.disable_module(module_id):
                bot.say("Unable to disable module {}, maybe it's not enabled?".format(module_id))
                return

            # Rebuild command cache
            bot.commands.rebuild()
            bot.say("Disabled module {}".format(module_id))

        elif sub_command == "enable":
            if len(msg_args) < 2:
                return
            module_id = msg_args[1].lower()

            module = module_manager.get_module(module_id)
            if not module:
                bot.say("No module with the id {} found".format(module_id))
                return

            if module.MODULE_TYPE > ModuleType.TYPE_NORMAL:
                bot.say("Unable to enable module {}".format(module_id))
                return

            if not module_manager.enable_module(module_id):
                bot.say("Unable to enable module {}, maybe it's already enabled?".format(module_id))
                return

            # Rebuild command cache
            bot.commands.rebuild()
            bot.say("Enabled module {}".format(module_id))

    def load_commands(self, **options):
        self.commands["w"] = Command.raw_command(self.whisper, level=2000, description="Send a whisper from the bot")
        self.commands["editpoints"] = Command.raw_command(
            self.edit_points,
            level=1500,
            description="Modifies a user's points",
            examples=[
                CommandExample(
                    None,
                    "Give a user points",
                    chat="user:!editpoints pajlada 500\n" "bot>user:Successfully gave pajlada 500 points.",
                    description="This creates 500 points and gives them to pajlada",
                ).parse(),
                CommandExample(
                    None,
                    "Remove points from a user",
                    chat="user:!editpoints pajlada -500\n" "bot>user:Successfully removed 500 points from pajlada.",
                    description="This removes 500 points from pajlada. Users can go into negative points with this.",
                ).parse(),
            ],
        )
        self.commands["setpoints"] = Command.raw_command(
            self.set_points,
            level=1500,
            description="Sets a user's points",
            examples=[
                CommandExample(
                    None,
                    "Set a user's points",
                    chat="user:!setpoints pajlada 500\n" "bot>user:Successfully set pajlada's points to 500.",
                    description="This sets pajlada's points to 500.",
                ).parse()
            ],
        )
        self.commands["level"] = Command.raw_command(self.level, level=1000, description="Set a users level")

        self.commands["silence"] = Command.raw_command(self.cmd_silence, level=500, description="Silence the bot")
        self.commands["mute"] = self.commands["silence"]

        self.commands["unsilence"] = Command.raw_command(self.cmd_unsilence, level=500, description="Unsilence the bot")
        self.commands["unmute"] = self.commands["unsilence"]

        self.commands["module"] = Command.raw_command(self.cmd_module, level=500, description="Modify module")

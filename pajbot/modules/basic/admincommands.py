import logging

from pajbot.managers.adminlog import AdminLogManager
from pajbot.managers.db import DBManager
from pajbot.models.command import Command
from pajbot.models.command import CommandExample
from pajbot.models.module import Module
from pajbot.models.user import User
from pajbot.modules import BaseModule
from pajbot.modules import ModuleType
from pajbot.modules.basic import BasicCommandsModule
from pajbot.utils import split_into_chunks_with_prefix

log = logging.getLogger(__name__)


class AdminCommandsModule(BaseModule):
    ID = __name__.split(".")[-1]
    NAME = "Admin Commands"
    DESCRIPTION = "All miscellaneous admin commands"
    CATEGORY = "Feature"
    ENABLED_DEFAULT = True
    MODULE_TYPE = ModuleType.TYPE_ALWAYS_ENABLED
    PARENT_MODULE = BasicCommandsModule

    @staticmethod
    def whisper(bot, message, **rest):
        if not message:
            return False

        msg_args = message.split(" ")
        if len(msg_args) > 1:
            username = msg_args[0]
            rest = " ".join(msg_args[1:])
            bot.whisper_login(username, rest)

    def edit_points(self, bot, source, message, **rest):
        if not message:
            return False

        msg_split = message.split(" ")
        if len(msg_split) < 2:
            # The user did not supply enough arguments
            bot.whisper(source, f"Usage: !{self.command_name} USERNAME POINTS")
            return False

        username_input = msg_split[0]

        try:
            num_points = int(msg_split[1])
        except (ValueError, TypeError):
            # The user did not specify a valid integer for points
            bot.whisper(source, f"Invalid amount of points. Usage: !{self.command_name} USERNAME POINTS")
            return False

        with DBManager.create_session_scope() as db_session:
            user = User.find_by_user_input(db_session, username_input)
            if not user:
                bot.whisper(source, "This user does not exist FailFish")
                return False

            user.points += num_points

            if num_points >= 0:
                bot.whisper(source, f"Successfully gave {user} {num_points} points.")
            else:
                bot.whisper(source, f"Successfully removed {abs(num_points)} points from {user}.")

    def set_points(self, bot, source, message, **rest):
        if not message:
            return False

        msg_split = message.split(" ")
        if len(msg_split) < 2:
            # The user did not supply enough arguments
            bot.whisper(source, f"Usage: !{self.command_name} USERNAME POINTS")
            return False

        username = msg_split[0]
        if len(username) < 2:
            # The username specified was too short. ;-)
            return False

        try:
            num_points = int(msg_split[1])
        except (ValueError, TypeError):
            # The user did not specify a valid integer for points
            bot.whisper(source, f"Invalid amount of points. Usage: !{self.command_name} USERNAME POINTS")
            return False

        with DBManager.create_session_scope() as db_session:
            user = User.find_by_user_input(db_session, username)
            if not user:
                bot.whisper(source, "This user does not exist FailFish")
                return False

            user.points = num_points

            bot.whisper(source, f"Successfully set {user}'s points to {num_points}.")

    @staticmethod
    def level(bot, source, message, **rest):
        if not message:
            bot.whisper(source, "Usage: !level USERNAME NEW_LEVEL")
            return False

        msg_args = message.split(" ")
        if len(msg_args) < 2:
            return False

        username = msg_args[0].lower()
        new_level = int(msg_args[1])
        if new_level >= source.level:
            bot.whisper(source, f"You cannot promote someone to the same or higher level as you ({source.level}).")
            return False

        # We create the user if the user didn't already exist in the database.
        with DBManager.create_session_scope() as db_session:
            user = User.find_or_create_from_user_input(db_session, bot.twitch_helix_api, username)
            if user is None:
                bot.whisper(source, f'A user with the name "{username}" could not be found.')
                return False

            if user.level >= source.level:
                bot.whisper(
                    source,
                    f"You cannot change the level of someone who is the same or higher level than you. You are level {source.level}, and {username} is level {user.level}",
                )
                return False

            old_level = user.level
            user.level = new_level

            log_msg = f"{user}'s user level changed from {old_level} to {new_level}"

            bot.whisper(source, log_msg)

            AdminLogManager.add_entry("Userlevel edited", source, log_msg)

    @staticmethod
    def cmd_silence(bot, source, **rest):
        if bot.silent:
            bot.whisper(source, "The bot is already silent")
        else:
            bot.silent = True
            bot.whisper(
                source,
                "The bot is now silent. Use !unsilence to enable messages again. Note that this option does not stick in case the bot crashes or restarts",
            )

    @staticmethod
    def cmd_unsilence(bot, source, **rest):
        if not bot.silent:
            bot.whisper(source, "The bot can already talk")
        else:
            bot.silent = False
            bot.whisper(source, "The bot can now talk again")

    @staticmethod
    def cmd_module(bot, source, message, **options):
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
                bot.say(f"No module with the id {module_id} found")
                return

            if module.MODULE_TYPE > ModuleType.TYPE_NORMAL:
                bot.say(f"Unable to disable module {module_id}")
                return

            if not module_manager.disable_module(module_id):
                bot.say(f"Unable to disable module {module_id}, maybe it's not enabled?")
                return

            # Rebuild command cache
            bot.commands.rebuild()

            with DBManager.create_session_scope() as db_session:
                db_module = db_session.query(Module).filter_by(id=module_id).one()
                db_module.enabled = False

            AdminLogManager.post("Module toggled", source, "Disabled", module_id)

            bot.say(f"Disabled module {module_id}")

        elif sub_command == "enable":
            if len(msg_args) < 2:
                return
            module_id = msg_args[1].lower()

            module = module_manager.get_module(module_id)
            if not module:
                bot.say(f"No module with the id {module_id} found")
                return

            if module.MODULE_TYPE > ModuleType.TYPE_NORMAL:
                bot.say(f"Unable to enable module {module_id}")
                return

            if not module_manager.enable_module(module_id):
                bot.say(f"Unable to enable module {module_id}, maybe it's already enabled?")
                return

            # Rebuild command cache
            bot.commands.rebuild()

            with DBManager.create_session_scope() as db_session:
                db_module = db_session.query(Module).filter_by(id=module_id).one()
                db_module.enabled = True

            AdminLogManager.post("Module toggled", source, "Enabled", module_id)

            bot.say(f"Enabled module {module_id}")

    @staticmethod
    def twitter_follow(bot, source, message, event, args):
        if message:
            username = message.split(" ")[0].strip().lower()
            if bot.twitter_manager.follow_user(username):
                log_msg = f"Now following {username}"
                bot.whisper(source, log_msg)
                AdminLogManager.add_entry("Twitter user followed", source, log_msg)
            else:
                bot.whisper(
                    source,
                    f"An error occured while attempting to follow {username}, perhaps we are already following this person?",
                )

    @staticmethod
    def twitter_unfollow(bot, source, message, event, args):
        if message:
            username = message.split(" ")[0].strip().lower()
            if bot.twitter_manager.unfollow_user(username):
                log_msg = f"No longer following {username}"
                bot.whisper(source, log_msg)
                AdminLogManager.add_entry("Twitter user unfollowed", source, log_msg)
            else:
                bot.whisper(
                    source,
                    f"An error occured while attempting to unfollow {username}, perhaps we are not following this person?",
                )

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

        self.commands["module"] = Command.raw_command(
            self.cmd_module, level=500, description="Modify module", delay_all=0, delay_user=0
        )

        self.commands["twitterfollow"] = Command.raw_command(
            self.twitter_follow,
            level=1000,
            description="Start listening for tweets for the given user",
            examples=[
                CommandExample(
                    None,
                    "Default usage",
                    chat="user:!twitterfollow forsen\n" "bot>user:Now following Forsen",
                    description="Follow Forsen on twitter so new tweets are output in chat.",
                ).parse()
            ],
        )

        self.commands["twitterunfollow"] = Command.raw_command(
            self.twitter_unfollow,
            level=1000,
            description="Stop listening for tweets for the given user",
            examples=[
                CommandExample(
                    None,
                    "Default usage",
                    chat="user:!twitterunfollow forsen\n" "bot>user:No longer following Forsen",
                    description="Stop automatically printing tweets from Forsen",
                ).parse()
            ],
        )

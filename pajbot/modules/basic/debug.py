import collections
import logging

from pajbot.managers.db import DBManager
from pajbot.models.command import Command, CommandExample
from pajbot.models.user import User
from pajbot.modules import BaseModule, ModuleType
from pajbot.modules.basic import BasicCommandsModule

log = logging.getLogger(__name__)


class DebugModule(BaseModule):

    ID = __name__.split(".")[-1]
    NAME = "Debug"
    DESCRIPTION = "Debug commands and users"
    CATEGORY = "Feature"
    ENABLED_DEFAULT = True
    MODULE_TYPE = ModuleType.TYPE_ALWAYS_ENABLED
    PARENT_MODULE = BasicCommandsModule
    HIDDEN = True

    @staticmethod
    def debug_command(bot, source, message, **rest):
        if not message or len(message) <= 0:
            bot.whisper(source, "Usage: !debug command (COMMAND_ID|COMMAND_ALIAS)")
            return False

        try:
            command_id = int(message)
        except ValueError:
            command_id = -1

        command = None

        if command_id == -1:
            potential_cmd = "".join(message.split(" ")[:1]).lower()
            if potential_cmd in bot.commands:
                command = bot.commands[potential_cmd]
        else:
            for _, potential_cmd in bot.commands.items():
                if potential_cmd.id == command_id:
                    command = potential_cmd
                    break

        if command is None:
            bot.whisper(source, "No command found with the given parameters.")
            return False

        data = collections.OrderedDict()
        data["id"] = command.id
        data["level"] = command.level
        data["type"] = command.action.type if command.action is not None else "???"
        data["cost"] = command.cost
        data["cd_all"] = command.delay_all
        data["cd_user"] = command.delay_user
        data["mod_only"] = command.mod_only
        data["sub_only"] = command.sub_only

        if data["type"] == "message":
            data["response"] = command.action.response
        elif data["type"] == "func" or data["type"] == "rawfunc":
            data["cb"] = command.action.cb.__name__

        bot.whisper(source, ", ".join(["%s=%s" % (key, value) for (key, value) in data.items()]))

    @staticmethod
    def debug_user(bot, source, message, **options):
        if not message or len(message) <= 0:
            bot.whisper(source, "Usage: !debug user USERNAME")
            return False

        username = message.split(" ")[0]
        with DBManager.create_session_scope() as db_session:
            user = User.find_by_user_input(db_session, username)

            if user is None:
                bot.whisper(source, "No user with this username found.")
                return False

            # TODO the time_in_chat_ properties could be displayed in a more user-friendly way
            #  current output format is time_in_chat_online=673800.0, time_in_chat_offline=7651200.0
            data = user.jsonify()

            bot.whisper(source, ", ".join([f"{key}={value}" for (key, value) in data.items()]))

    def load_commands(self, **options):
        self.commands["debug"] = Command.multiaction_command(
            level=100,
            delay_all=0,
            delay_user=0,
            default=None,
            commands={
                "command": Command.raw_command(
                    self.debug_command,
                    level=250,
                    description="Debug a command",
                    examples=[
                        CommandExample(
                            None,
                            "Debug a command",
                            chat="user:!debug command ping\n"
                            "bot>user: id=210, level=100, type=message, cost=0, cd_all=10, cd_user=30, mod_only=False, sub_only=False, response=Snusbot has been online for $(tb:bot_uptime)",
                            description="",
                        ).parse()
                    ],
                ),
                "user": Command.raw_command(
                    self.debug_user,
                    level=250,
                    description="Debug a user",
                    examples=[
                        CommandExample(
                            None,
                            "Debug a user",
                            chat="user:!debug user snusbot\n"
                            "bot>user: id=123, login=snusbot, name=Snusbot, level=100, num_lines=45, points=225, tokens=0, last_seen=2016-04-05 17:56:23 CEST, last_active=2016-04-05 17:56:07 CEST, ignored=False, banned=False",
                            description="",
                        ).parse()
                    ],
                ),
            },
        )

import argparse
import logging
from collections import UserDict

from sqlalchemy.orm import joinedload

from pajbot.managers.db import DBManager
from pajbot.models.command import Command
from pajbot.models.command import CommandData
from pajbot.models.command import CommandExample
from pajbot.models.command import parse_command_for_web
from pajbot.utils import find

log = logging.getLogger(__name__)


class CommandManager(UserDict):
    """This class is responsible for compiling commands from multiple sources
    into one easily accessible source.
    The following sources are used:
     - internal_commands = Commands that are added in source
     - db_commands = Commands that are loaded from the database
     - module_commands = Commands that are loaded from enabled modules

    """

    def __init__(self, socket_manager=None, module_manager=None, bot=None):
        UserDict.__init__(self)
        self.db_session = DBManager.create_session()

        self.internal_commands = {}
        self.db_commands = {}
        self.module_commands = {}
        self.data = {}

        self.bot = bot
        self.module_manager = module_manager

        if socket_manager:
            socket_manager.add_handler("module.update", self.on_module_reload)
            socket_manager.add_handler("command.update", self.on_command_update)
            socket_manager.add_handler("command.remove", self.on_command_remove)

    def on_module_reload(self, _data):
        log.debug("Rebuilding commands...")
        self.rebuild()
        log.debug("Done rebuilding commands")

    def on_command_update(self, data):
        try:
            command_id = int(data["command_id"])
        except (KeyError, ValueError):
            log.warning("No command ID found in on_command_update")
            return

        command = find(lambda command: command.id == command_id, self.db_commands.values())
        if command is not None:
            self.remove_command_aliases(command)

        self.load_by_id(command_id)

        log.debug(f"Reloaded command with id {command_id}")

        self.rebuild()

    def on_command_remove(self, data):
        try:
            command_id = int(data["command_id"])
        except (KeyError, ValueError):
            log.warning("No command ID found in on_command_update")
            return

        command = find(lambda command: command.id == command_id, self.db_commands.values())
        if command is None:
            log.warning("Invalid ID sent to on_command_update")
            return

        self.db_session.expunge(command.data)
        self.remove_command_aliases(command)

        log.debug(f"Remove command with id {command_id}")

        self.rebuild()

    def __del__(self):
        self.db_session.close()

    def commit(self):
        self.db_session.commit()

    def load_internal_commands(self):
        if self.internal_commands:
            return self.internal_commands

        self.internal_commands = {}

        self.internal_commands["quit"] = Command.pajbot_command(
            self.bot,
            "quit",
            level=1000,
            command="quit",
            description="Shut down the bot, this will most definitely restart it if set up properly",
        )

        self.internal_commands["1quit"] = self.internal_commands["quit"]
        self.internal_commands[
            "ceaseallactionscurrentlybeingacteduponwiththecodeandiapologizeforbeingawhitecisgenderedmaleinthepatriarchy"
        ] = self.internal_commands["quit"]

        self.internal_commands["add"] = Command.multiaction_command(
            level=100,
            delay_all=0,
            delay_user=0,
            default=None,
            command="add",
            commands={
                "command": Command.dispatch_command(
                    "add_command",
                    level=500,
                    description="Add a command!",
                    examples=[
                        CommandExample(
                            None,
                            "Create a normal command",
                            chat="user:!add command test Kappa 123\n" "bot>user:Added your command (ID: 7)",
                            description="This creates a normal command with the trigger !test which outputs Kappa 123 to chat",
                        ).parse(),
                        CommandExample(
                            None,
                            "Create a command that responds with a whisper",
                            chat="user:!add command test Kappa 123 --whisper\n" "bot>user:Added your command (ID: 7)",
                            description="This creates a command with the trigger !test which responds with Kappa 123 as a whisper to the user who called the command",
                        ).parse(),
                    ],
                ),
                "win": Command.dispatch_command("add_win", level=500, description="Add a win to something!"),
                "funccommand": Command.dispatch_command(
                    "add_funccommand", level=2000, description="Add a command that uses a command"
                ),
                "alias": Command.dispatch_command(
                    "add_alias",
                    level=500,
                    description="Adds an alias to an already existing command",
                    examples=[
                        CommandExample(
                            None,
                            "Add an alias to a command",
                            chat="user:!add alias test alsotest\n"
                            "bot>user:Successfully added the aliases alsotest to test",
                            description="Adds the alias !alsotest to the existing command !test",
                        ).parse(),
                        CommandExample(
                            None,
                            "Add multiple aliases to a command",
                            chat="user:!add alias test alsotest newtest test123\n"
                            "bot>user:Successfully added the aliases alsotest, newtest, test123 to test",
                            description="Adds the aliases !alsotest, !newtest, and !test123 to the existing command !test",
                        ).parse(),
                    ],
                ),
            },
        )
        self.internal_commands["edit"] = Command.multiaction_command(
            level=100,
            delay_all=0,
            delay_user=0,
            default=None,
            command="edit",
            commands={
                "command": Command.dispatch_command(
                    "edit_command",
                    level=500,
                    description="Edit an already-existing command",
                    examples=[
                        CommandExample(
                            None,
                            "Change the response",
                            chat="user:!edit command test This is the new response!\n"
                            "bot>user:Updated the command (ID: 29)",
                            description='Changes the text response for the command !test to "This is the new response!"',
                        ).parse(),
                        CommandExample(
                            None,
                            "Change the Global Cooldown",
                            chat="user:!edit command test --cd 10\n" "bot>user:Updated the command (ID: 29)",
                            description="Changes the global cooldown for the command !test to 10 seconds",
                        ).parse(),
                        CommandExample(
                            None,
                            "Change the User-specific Cooldown",
                            chat="user:!edit command test --usercd 30\n" "bot>user:Updated the command (ID: 29)",
                            description="Changes the user-specific cooldown for the command !test to 30 seconds",
                        ).parse(),
                        CommandExample(
                            None,
                            "Change the Level for a command",
                            chat="user:!edit command test --level 500\n" "bot>user:Updated the command (ID: 29)",
                            description="Changes the command level for !test to level 500",
                        ).parse(),
                        CommandExample(
                            None,
                            "Change the Cost for a command",
                            chat="user:!edit command $test1 --cost 50\n" "bot>user:Updated the command (ID: 27)",
                            description="Changes the command cost for !$test1 to 50 points, you should always use a $ for a command that cost points.",
                        ).parse(),
                        CommandExample(
                            None,
                            "Change a command to Moderator only",
                            chat="user:!edit command test --modonly\n" "bot>user:Updated the command (ID: 29)",
                            description="This command can only be used for user with level 100 and Moderator status or user over level 500",
                        ).parse(),
                        CommandExample(
                            None,
                            "Remove Moderator only from a command",
                            chat="user:!edit command test --no-modonly\n" "bot>user:Updated the command (ID: 29)",
                            description="This command can be used for normal users again.",
                        ).parse(),
                    ],
                ),
                "funccommand": Command.dispatch_command(
                    "edit_funccommand", level=2000, description="Edit a command that uses a command"
                ),
            },
        )
        self.internal_commands["remove"] = Command.multiaction_command(
            level=100,
            delay_all=0,
            delay_user=0,
            default=None,
            command="remove",
            commands={
                "command": Command.dispatch_command(
                    "remove_command",
                    level=500,
                    description="Remove a command!",
                    examples=[
                        CommandExample(
                            None,
                            "Remove a command",
                            chat="user:!remove command Keepo123\n" "bot>user:Successfully removed command with id 27",
                            description="Removes a command with the trigger !Keepo123",
                        ).parse(),
                        CommandExample(
                            None,
                            "Remove a command with the given ID.",
                            chat="user:!remove command 28\n" "bot>user:Successfully removed command with id 28",
                            description="Removes a command with id 28",
                        ).parse(),
                    ],
                ),
                "win": Command.dispatch_command("remove_win", level=500, description="Remove a win to something!"),
                "alias": Command.dispatch_command(
                    "remove_alias",
                    level=500,
                    description="Removes an alias to an already existing command",
                    examples=[
                        CommandExample(
                            None,
                            "Remove two aliases",
                            chat="user:!remove alias KeepoKeepo Keepo2Keepo\n"
                            "bot>user:Successfully removed 2 aliases.",
                            description="Removes KeepoKeepo and Keepo2Keepo as aliases",
                        ).parse()
                    ],
                ),
            },
        )
        self.internal_commands["rem"] = self.internal_commands["remove"]
        self.internal_commands["del"] = self.internal_commands["remove"]
        self.internal_commands["delete"] = self.internal_commands["remove"]
        self.internal_commands["eval"] = Command.dispatch_command(
            "eval", level=2000, description="Run a raw python command. Debug mode only"
        )

        return self.internal_commands

    def create_command(self, alias_str, **options):
        aliases = alias_str.lower().replace("!", "").split("|")
        for alias in aliases:
            if alias in self.data:
                return self.data[alias], False, alias

        command = Command(command=alias_str, **options)
        command.data = CommandData(command.id, **options)
        self.add_db_command_aliases(command)
        with DBManager.create_session_scope(expire_on_commit=False) as db_session:
            db_session.add(command)
            db_session.add(command.data)
            db_session.commit()
            db_session.expunge(command)
            db_session.expunge(command.data)
        self.db_session.add(command.data)
        self.commit()

        self.rebuild()
        return command, True, ""

    def edit_command(self, command_to_edit, **options):
        command_to_edit.set(**options)
        command_to_edit.data.set(**options)
        DBManager.session_add_expunge(command_to_edit)
        self.commit()

    def remove_command_aliases(self, command):
        aliases = command.command.split("|")
        for alias in aliases:
            if alias in self.db_commands:
                del self.db_commands[alias]
            else:
                log.warning(f"For some reason, {alias} was not in the list of commands when we removed it.")

    def remove_command(self, command):
        self.remove_command_aliases(command)

        with DBManager.create_session_scope() as db_session:
            self.db_session.expunge(command.data)
            db_session.delete(command.data)
            db_session.delete(command)

        self.rebuild()

    def add_db_command_aliases(self, command):
        aliases = command.command.split("|")
        for alias in aliases:
            self.db_commands[alias] = command

        return len(aliases)

    def load_db_commands(self, **options):
        """This method is only meant to be run once.
        Any further updates to the db_commands dictionary will be done
        in other methods.

        """

        if self.db_commands:
            return self.db_commands

        query = self.db_session.query(Command)

        if options.get("load_examples", False) is True:
            query = query.options(joinedload(Command.examples))
        if options.get("enabled", True) is True:
            query = query.filter_by(enabled=True)

        for command in query:
            self.add_db_command_aliases(command)
            self.db_session.expunge(command)
            if command.data is None:
                log.info(f"Creating command data for {command.command}")
                command.data = CommandData(command.id)
            self.db_session.add(command.data)

        return self.db_commands

    def rebuild(self):
        """Rebuild the internal commands list from all sources."""

        def merge_commands(in_dict, out):
            for alias, command in in_dict.items():
                if command.action:
                    # Resets any previous modifications to the action.
                    # Right now, the only thing this resets is the MultiAction
                    # command list.
                    command.action.reset()

                if alias in out:
                    if (
                        command.action
                        and command.action.type == "multi"
                        and out[alias].action
                        and out[alias].action.type == "multi"
                    ):
                        out[alias].action += command.action
                    else:
                        out[alias] = command
                else:
                    out[alias] = command

        self.data = {}
        db_commands = {alias: command for alias, command in self.db_commands.items() if command.enabled is True}

        merge_commands(self.internal_commands, self.data)
        merge_commands(db_commands, self.data)

        if self.module_manager is not None:
            for enabled_module in self.module_manager.modules:
                merge_commands(enabled_module.commands, self.data)

    def load(self, **options):
        self.load_internal_commands()
        self.load_db_commands(**options)

        self.rebuild()

        return self

    def load_by_id(self, command_id):
        self.db_session.commit()
        command = self.db_session.query(Command).filter_by(id=command_id, enabled=True).one_or_none()
        if command:
            self.add_db_command_aliases(command)
            self.db_session.expunge(command)
            if command.data is None:
                log.info(f"Creating command data for {command.command}")
                command.data = CommandData(command.id)
            self.db_session.add(command.data)

    def parse_for_web(self):
        commands = []

        for alias, command in self.data.items():
            parse_command_for_web(alias, command, commands)

        return commands

    @staticmethod
    def parse_command_arguments(message):
        parser = argparse.ArgumentParser()
        parser.add_argument("--whisper", dest="whisper", action="store_true")
        parser.add_argument("--no-whisper", dest="whisper", action="store_false")
        parser.add_argument("--reply", dest="reply", action="store_true")
        parser.add_argument("--no-reply", dest="reply", action="store_false")
        parser.add_argument("--cd", type=int, dest="delay_all")
        parser.add_argument("--usercd", type=int, dest="delay_user")
        parser.add_argument("--level", type=int, dest="level")
        parser.add_argument("--cost", type=int, dest="cost")
        parser.add_argument("--tokens-cost", type=int, dest="tokens_cost")
        parser.add_argument("--modonly", dest="mod_only", action="store_true")
        parser.add_argument("--no-modonly", dest="mod_only", action="store_false")
        parser.add_argument("--subonly", dest="sub_only", action="store_true")
        parser.add_argument("--no-subonly", dest="sub_only", action="store_false")
        parser.add_argument("--checkmsg", dest="run_through_banphrases", action="store_true")
        parser.add_argument("--no-checkmsg", dest="run_through_banphrases", action="store_false")

        try:
            args, unknown = parser.parse_known_args(message)
        except SystemExit:
            return False, False
        except:
            log.exception("Unhandled exception in add_command")
            return False, False

        # Strip options of any values that are set as None
        options = {k: v for k, v in vars(args).items() if v is not None}
        response = " ".join(unknown)

        if "cost" in options:
            options["cost"] = abs(options["cost"])
        if "tokens_cost" in options:
            options["tokens_cost"] = abs(options["tokens_cost"])

        return options, response

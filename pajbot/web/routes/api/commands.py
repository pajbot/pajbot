import json
import logging

from flask_restful import Resource
from flask_restful import reqparse
from sqlalchemy.orm import joinedload

import pajbot.modules
import pajbot.utils
import pajbot.web.utils
from pajbot.managers.adminlog import AdminLogManager
from pajbot.managers.db import DBManager
from pajbot.models.command import Command
from pajbot.models.command import CommandData
from pajbot.models.module import ModuleManager
from pajbot.models.sock import SocketClientManager
from pajbot.utils import find

log = logging.getLogger(__name__)


class APICommands(Resource):
    @staticmethod
    def get():
        commands = pajbot.web.utils.get_cached_commands()

        commands = list(filter(lambda c: c["id"] is not None, commands))

        return {"commands": commands}, 200


class APICommand(Resource):
    @staticmethod
    def get(raw_command_id):
        command_string = raw_command_id
        command_id = None

        try:
            command_id = int(command_string)
        except (ValueError, TypeError):
            pass

        if command_id:
            command = find(lambda c: c["id"] == command_id, pajbot.web.utils.get_cached_commands())
        else:
            command = find(lambda c: c["resolve_string"] == command_string, pajbot.web.utils.get_cached_commands())

        if not command:
            return {"message": "A command with the given ID was not found."}, 404

        return {"command": command}, 200


class APICommandRemove(Resource):
    @pajbot.web.utils.requires_level(500)
    def get(self, command_id, **options):
        with DBManager.create_session_scope() as db_session:
            command = db_session.query(Command).filter_by(id=command_id).one_or_none()
            if command is None:
                return {"error": "Invalid command ID"}, 404
            if command.level > options["user"].level:
                return {"error": "Unauthorized"}, 403
            log_msg = f"The !{command.command.split('|')[0]} command has been removed"
            AdminLogManager.add_entry("Command removed", options["user"], log_msg)
            db_session.delete(command.data)
            db_session.delete(command)

        if SocketClientManager.send("command.remove", {"command_id": command_id}) is True:
            return {"success": "good job"}, 200
        else:
            return {"error": "could not push update"}, 500


class APICommandUpdate(Resource):
    def __init__(self):
        super().__init__()

        self.post_parser = reqparse.RequestParser()
        self.post_parser.add_argument("data_level", required=False)
        self.post_parser.add_argument("data_enabled", required=False)
        self.post_parser.add_argument("data_delay_all", required=False)
        self.post_parser.add_argument("data_delay_user", required=False)
        self.post_parser.add_argument("data_cost", required=False)
        self.post_parser.add_argument("data_can_execute_with_whisper", required=False)
        self.post_parser.add_argument("data_sub_only", required=False)
        self.post_parser.add_argument("data_action_type", required=False)
        self.post_parser.add_argument("data_action_message", required=False)

    @pajbot.web.utils.requires_level(500)
    def post(self, command_id, **extra_args):
        args = pajbot.utils.remove_none_values(self.post_parser.parse_args())
        if len(args) == 0:
            return {"error": "Missing parameter to edit."}, 400

        valid_names = ["enabled", "level", "delay_all", "delay_user", "cost", "can_execute_with_whisper", "sub_only"]

        valid_action_names = ["type", "message"]

        with DBManager.create_session_scope() as db_session:
            command = (
                db_session.query(Command)
                .options(joinedload(Command.data).joinedload(CommandData.user))
                .filter_by(id=command_id)
                .one_or_none()
            )
            if command is None:
                return {"error": "Invalid command ID"}, 404

            if command.level > extra_args["user"].level:
                return {"error": "Unauthorized"}, 403
            parsed_action = json.loads(command.action_json)
            options = {"edited_by": extra_args["user"].id}

            for key in args:
                if key.startswith("data_"):
                    name = key[5:]
                    value = args[key]

                    if name.startswith("action_"):
                        name = name[7:]
                        if name in valid_action_names and name in parsed_action and command.action.type == "message":
                            value_type = type(parsed_action[name])
                            if value_type is bool:
                                parsed_value = True if value == "1" else False
                            elif value_type is int:
                                try:
                                    parsed_value = int(value)
                                except ValueError:
                                    continue
                            else:
                                parsed_value = value
                            parsed_action[name] = parsed_value
                        command.action_json = json.dumps(parsed_action)
                    else:
                        if name in valid_names:
                            value_type = type(getattr(command, name))
                            if value_type is bool:
                                parsed_value = True if value == "1" else False
                            elif value_type is int:
                                try:
                                    parsed_value = int(value)
                                except ValueError:
                                    continue
                            else:
                                parsed_value = value
                            options[name] = parsed_value

            aj = json.loads(command.action_json)
            old_message = ""
            new_message = ""
            try:
                old_message = command.action.response
                new_message = aj["message"]
            except:
                pass

            command.set(**options)
            command.data.set(**options)

            if len(old_message) > 0 and old_message != new_message:
                log_msg = f'The !{command.command.split("|")[0]} command has been updated from "{old_message}" to "{new_message}"'
            else:
                log_msg = f"The !{command.command.split('|')[0]} command has been updated"

            AdminLogManager.add_entry(
                "Command edited",
                extra_args["user"],
                log_msg,
                data={"old_message": old_message, "new_message": new_message},
            )

        if SocketClientManager.send("command.update", {"command_id": command_id}) is True:
            return {"success": "good job"}, 200
        else:
            return {"error": "could not push update"}, 500


class APICommandCheckAlias(Resource):
    def __init__(self):
        super().__init__()

        self.post_parser = reqparse.RequestParser()
        self.post_parser.add_argument("alias", required=True)

    @pajbot.web.utils.requires_level(500)
    def post(self, **extra_args):
        args = pajbot.utils.remove_none_values(self.post_parser.parse_args())

        request_alias = args["alias"].lower()

        command_manager = pajbot.managers.command.CommandManager(
            socket_manager=None, module_manager=ModuleManager(None).load(), bot=None
        ).load(enabled=None)

        command_aliases = []

        for alias, command in command_manager.items():
            command_aliases.append(alias)
            if command.command and len(command.command) > 0:
                command_aliases.extend(command.command.split("|"))

        command_aliases = set(command_aliases)

        if request_alias in command_aliases:
            return {"error": "Alias already in use"}
        else:
            return {"success": "good job"}


def init(api):
    api.add_resource(APICommands, "/commands")
    api.add_resource(APICommand, "/commands/<raw_command_id>")
    api.add_resource(APICommandRemove, "/commands/remove/<int:command_id>")
    api.add_resource(APICommandUpdate, "/commands/update/<int:command_id>")
    api.add_resource(APICommandCheckAlias, "/commands/checkalias")

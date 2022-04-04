from typing import Optional

import json
import logging
from dataclasses import dataclass

import pajbot.modules
import pajbot.utils
import pajbot.web.utils
from pajbot.managers.adminlog import AdminLogManager
from pajbot.managers.db import DBManager
from pajbot.models.command import Command, CommandData
from pajbot.models.module import ModuleManager
from pajbot.models.sock import SocketClientManager
from pajbot.utils import find

import marshmallow_dataclass
from flask import Blueprint, request
from flask.typing import ResponseReturnValue
from marshmallow import ValidationError
from sqlalchemy.orm import joinedload

log = logging.getLogger(__name__)


@dataclass
class CheckAlias:
    alias: str


CheckAliasSchema = marshmallow_dataclass.class_schema(CheckAlias)


@dataclass
class CommandUpdate:
    data_enabled: Optional[bool]
    data_delay_all: Optional[int]
    data_delay_user: Optional[int]
    data_cost: Optional[int]
    data_can_execute_with_whisper: Optional[bool]
    data_sub_only: Optional[bool]
    data_mod_only: Optional[bool]
    data_action_type: Optional[str]
    data_action_message: Optional[str]
    data_use_global_cd: Optional[bool]
    run_through_banphrases: Optional[bool]
    data_level: Optional[int]


CommandUpdateSchema = marshmallow_dataclass.class_schema(CommandUpdate)


def init(bp: Blueprint) -> None:
    @bp.route("/commands")
    def commands():
        commands = pajbot.web.utils.get_cached_commands()

        commands = list(filter(lambda c: c["id"] is not None, commands))

        return {"commands": commands}, 200

    @bp.route("/commands/<raw_command_id>")
    def command_get(raw_command_id):
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

    @bp.route("/commands/remove/<int:command_id>", methods=["POST"])
    @pajbot.web.utils.requires_level(500)
    def command_remove(command_id, **options):
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

    @bp.route("/commands/update/<int:command_id>", methods=["POST"])
    @pajbot.web.utils.requires_level(500)
    def command_update(command_id: int, **extra_args) -> ResponseReturnValue:
        try:
            json_data = request.get_json()
            if not json_data:
                return {"error": "Missing json body"}, 400
            data: CommandUpdate = CommandUpdateSchema().load(json_data)
        except ValidationError as err:
            return {"error": f"Did not match schema: {json.dumps(err.messages)}"}, 400

        payload = pajbot.utils.remove_none_values(CommandUpdateSchema().dump(data))

        if not payload:
            return {"error": "Must edit at least one value"}, 400

        # Remove action_ fields from payload, they will be parsed manually below
        payload = {k: v for k, v in payload.items() if not k.startswith("data_action")}

        # Strip data prefix from fields
        payload = {k[5:]: v for k, v in payload.items() if k.startswith("data_")}

        payload["edited_by"] = extra_args["user"].id

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
            if data.data_action_type:
                parsed_action["type"] = data.data_action_type
            if data.data_action_message:
                parsed_action["message"] = data.data_action_message
            command.action_json = json.dumps(parsed_action)

            aj = json.loads(command.action_json)
            old_message = ""
            new_message = ""
            try:
                old_message = command.action.response
                new_message = aj["message"]
            except:
                pass

            command.set(**payload)
            command.data.set(**payload)

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

    @bp.route("/commands/checkalias", methods=["POST"])
    @pajbot.web.utils.requires_level(500)
    def command_checkalias(**extra_args):
        json_data = request.get_json()
        if not json_data:
            return {"error": "No input data provided"}, 400
        try:
            data = CheckAliasSchema().load(json_data)
        except ValidationError as err:
            return {"error": f"Did not match schema: {json.dumps(err.messages)}"}, 400

        request_alias = data.alias.lower()

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

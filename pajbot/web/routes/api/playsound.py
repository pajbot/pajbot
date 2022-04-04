from typing import Optional

import json
import logging
from dataclasses import dataclass

from pajbot.managers.adminlog import AdminLogManager
from pajbot.managers.db import DBManager
from pajbot.models.playsound import Playsound
from pajbot.models.sock import SocketClientManager
from pajbot.modules import PlaysoundModule
from pajbot.web.utils import requires_level

import marshmallow_dataclass
from flask import Blueprint, request
from flask.typing import ResponseReturnValue
from marshmallow import ValidationError

log = logging.getLogger(__name__)


@dataclass
class CreatePlaysound:
    link: str
    name: str


CreatePlaysoundSchema = marshmallow_dataclass.class_schema(CreatePlaysound)


@dataclass
class UpdatePlaysound(CreatePlaysound):
    volume: int
    enabled: bool
    cooldown: Optional[int]


UpdatePlaysoundSchema = marshmallow_dataclass.class_schema(UpdatePlaysound)


def init(bp: Blueprint) -> None:
    @bp.route("/playsound/<playsound_name>", methods=["PUT"])
    @requires_level(500)
    def playsound_create(playsound_name: str, **options) -> ResponseReturnValue:
        # Create playsound
        playsound_name = PlaysoundModule.massage_name(playsound_name)

        if not PlaysoundModule.validate_name(playsound_name):
            return (
                {
                    "error": "Invalid Playsound name. The playsound name may only contain lowercase latin letters, 0-9, -, or _. No spaces :rage:"
                },
                400,
            )

        try:
            json_data = request.get_json()
            if not json_data:
                return {"error": "Missing json body"}, 400
            data = CreatePlaysoundSchema().load(json_data)
        except ValidationError as err:
            return {"error": f"Did not match schema: {json.dumps(err.messages)}"}, 400

        with DBManager.create_session_scope() as db_session:
            count = db_session.query(Playsound).filter(Playsound.name == playsound_name).count()
            if count >= 1:
                return "Playsound already exists", 400

            # the rest of the parameters are initialized with defaults
            playsound = Playsound(name=playsound_name, link=data.link)
            db_session.add(playsound)
            log_msg = f"The {playsound_name} playsound has been added"
            AdminLogManager.add_entry("Playsound added", options["user"], log_msg)

            return "OK", 200

    @bp.route("/playsound/<playsound_name>", methods=["POST"])
    @requires_level(500)
    def playsound_edit(playsound_name: str, **options) -> ResponseReturnValue:
        # Update playsound
        try:
            json_data = request.get_json()
            if not json_data:
                return {"error": "Missing json body"}, 400
            data: UpdatePlaysound = UpdatePlaysoundSchema().load(json_data)
        except ValidationError as err:
            return {"error": f"Did not match schema: {json.dumps(err.messages)}"}, 400

        # require JSON so the cooldown can be null

        link = data.link
        # TODO: Migrate to validator
        if not PlaysoundModule.validate_link(link):
            return "Empty or bad link, links must start with https:// and must not contain spaces", 400

        volume = data.volume
        # TODO: Migrate to validator
        if not PlaysoundModule.validate_volume(volume):
            return "Bad volume argument", 400

        # cooldown is allowed to be null/None
        cooldown = data.cooldown
        # TODO: Migrate to validator
        if not PlaysoundModule.validate_cooldown(cooldown):
            return "Bad cooldown argument", 400

        enabled = data.enabled
        # TODO: Migrate to validator
        if enabled is None:
            return "Bad enabled argument", 400

        with DBManager.create_session_scope() as db_session:
            playsound = db_session.query(Playsound).filter(Playsound.name == playsound_name).one_or_none()

            if playsound is None:
                return "Playsound does not exist", 404

            raw_edited_data = {
                "link": (playsound.link, link),
                "volume": (playsound.volume, volume),
                "cooldown": (playsound.cooldown, cooldown),
            }
            # make a dictionary with all the changed values (except for enabled, which has a special case below)
            filtered_edited_data = {k: v for k, v in raw_edited_data.items() if v[0] != v[1]}

            log_msg = f"The {playsound_name} playsound has been updated: "
            log_msg_changes = []

            if playsound.enabled != enabled:
                log_msg_changes.append("enabled" if enabled else "disabled")

            # iterate over changed values and push them to the log msg
            for edited_key, values in filtered_edited_data.items():
                log_msg_changes.append(f"{edited_key} {values[0]} to {values[1]}")

            log_msg += ", ".join(log_msg_changes)

            playsound.link = link
            playsound.volume = volume
            playsound.cooldown = cooldown
            playsound.enabled = enabled

            db_session.add(playsound)

            if len(log_msg_changes):
                AdminLogManager.add_entry("Playsound edited", options["user"], log_msg)

        return "OK", 200

    @bp.route("/playsound/<playsound_name>", methods=["DELETE"])
    @requires_level(500)
    def playsound_delete(playsound_name: str, **options) -> ResponseReturnValue:
        with DBManager.create_session_scope() as db_session:
            playsound = db_session.query(Playsound).filter(Playsound.name == playsound_name).one_or_none()

            if playsound is None:
                return "Playsound does not exist", 404

            log_msg = f"The {playsound.name} playsound has been removed"
            AdminLogManager.add_entry("Playsound removed", options["user"], log_msg)
            db_session.delete(playsound)

            return "OK", 200

    @bp.route("/playsound/<playsound_name>/play", methods=["POST"])
    @requires_level(500)
    def playsound_play(playsound_name: str, **options) -> ResponseReturnValue:
        with DBManager.create_session_scope() as db_session:
            count = db_session.query(Playsound).filter(Playsound.name == playsound_name).count()

            if count <= 0:
                return "Playsound does not exist", 404
            # explicitly don't check for disabled

        SocketClientManager.send("playsound.play", {"name": playsound_name})

        return "OK", 200

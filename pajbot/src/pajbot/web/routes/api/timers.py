import json
import logging

import pajbot.modules
import pajbot.utils
import pajbot.web.utils
from pajbot.managers.adminlog import AdminLogManager
from pajbot.managers.db import DBManager
from pajbot.models.sock import SocketClientManager
from pajbot.models.timer import Timer
from pajbot.web.schemas.toggle_state import ToggleState, ToggleStateSchema

from flask import Blueprint, request
from flask.typing import ResponseReturnValue
from marshmallow import ValidationError

log = logging.getLogger(__name__)


def init(bp: Blueprint) -> None:
    @bp.route("/timers/remove/<int:timer_id>", methods=["POST"])
    @pajbot.web.utils.requires_level(500)
    def timer_remove(timer_id: int, **options) -> ResponseReturnValue:
        with DBManager.create_session_scope() as db_session:
            timer = db_session.query(Timer).filter_by(id=timer_id).one_or_none()
            if timer is None:
                return {"error": "Invalid timer ID"}, 404
            AdminLogManager.post("Timer removed", options["user"], timer.name)
            db_session.delete(timer)
            SocketClientManager.send("timer.remove", {"id": timer.id})
            return {"success": "good job"}

    @bp.route("/timers/toggle/<int:timer_id>", methods=["POST"])
    @pajbot.web.utils.requires_level(500)
    def timer_toggle(timer_id: int, **options) -> ResponseReturnValue:
        try:
            json_data = request.get_json()
            if not json_data:
                return {"error": "Missing json body"}, 400
            data: ToggleState = ToggleStateSchema().load(json_data)
        except ValidationError as err:
            return {"error": f"Did not match schema: {json.dumps(err.messages)}"}, 400

        with DBManager.create_session_scope() as db_session:
            row = db_session.query(Timer).filter_by(id=timer_id).one_or_none()

            if not row:
                return {"error": "Timer with this ID not found"}, 404

            row.enabled = data.new_state
            db_session.commit()
            payload = {"id": row.id, "new_state": data.new_state}
            AdminLogManager.post(
                "Timer toggled", options["user"], "Enabled" if data.new_state else "Disabled", row.name
            )
            SocketClientManager.send("timer.update", payload)
            return {"success": "successful toggle", "new_state": data.new_state}

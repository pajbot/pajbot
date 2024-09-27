import json
import logging

import pajbot.modules
import pajbot.utils
import pajbot.web.utils
from pajbot.managers.adminlog import AdminLogManager
from pajbot.managers.db import DBManager
from pajbot.models.module import Module
from pajbot.models.sock import SocketClientManager
from pajbot.modules.base import ModuleType
from pajbot.utils import find
from pajbot.web.schemas.toggle_state import ToggleState, ToggleStateSchema

from flask import Blueprint, request
from flask.typing import ResponseReturnValue
from marshmallow import ValidationError

log = logging.getLogger(__name__)


def validate_module(module_id):
    module = find(lambda m: m.ID == module_id, pajbot.modules.available_modules)

    if module is None:
        return False

    return module.MODULE_TYPE not in (ModuleType.TYPE_ALWAYS_ENABLED,)


def init(bp: Blueprint) -> None:
    @bp.route("/modules/toggle/<row_id>", methods=["POST"])
    @pajbot.web.utils.requires_level(500)
    def module_toggle(row_id: str, **options) -> ResponseReturnValue:
        try:
            json_data = request.get_json()
            if not json_data:
                return {"error": "Missing json body"}, 400
            data: ToggleState = ToggleStateSchema().load(json_data)
        except ValidationError as err:
            return {"error": f"Did not match schema: {json.dumps(err.messages)}"}, 400

        with DBManager.create_session_scope() as db_session:
            row = db_session.query(Module).filter_by(id=row_id).one_or_none()

            if not row:
                return {"error": "Module with this ID not found"}, 404

            if validate_module(row_id) is False:
                return {"error": "cannot modify module"}, 400

            row.enabled = data.new_state
            db_session.commit()
            payload = {"id": row.id, "new_state": data.new_state}
            AdminLogManager.post("Module toggled", options["user"], "Enabled" if row.enabled else "Disabled", row.id)
            SocketClientManager.send("module.update", payload)
            log.info(f"new state: {data} - {data.new_state}")
            return {"success": "successful toggle", "new_state": data.new_state}

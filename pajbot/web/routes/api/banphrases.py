import json
import logging
from dataclasses import dataclass

import pajbot.modules
import pajbot.utils
import pajbot.web.utils
from pajbot.managers.adminlog import AdminLogManager
from pajbot.managers.db import DBManager
from pajbot.models.banphrase import Banphrase, BanphraseManager
from pajbot.models.sock import SocketClientManager
from pajbot.web.schemas.toggle_state import ToggleState, ToggleStateSchema

import marshmallow_dataclass
from flask import Blueprint, request
from marshmallow import Schema, ValidationError

log = logging.getLogger(__name__)


@dataclass
class TestBanphrase(Schema):
    message: str


TestBanphraseSchema = marshmallow_dataclass.class_schema(TestBanphrase)


def init(bp: Blueprint) -> None:
    @bp.route("/banphrases/remove/<int:banphrase_id>", methods=["POST"])
    @pajbot.web.utils.requires_level(500)
    def banphrases_remove(banphrase_id, **options):
        with DBManager.create_session_scope() as db_session:
            banphrase = db_session.query(Banphrase).filter_by(id=banphrase_id).one_or_none()
            if banphrase is None:
                return {"error": "Invalid banphrase ID"}, 404
            AdminLogManager.post("Banphrase removed", options["user"], banphrase.id, banphrase.phrase)
            db_session.delete(banphrase)
            db_session.delete(banphrase.data)
            SocketClientManager.send("banphrase.remove", {"id": banphrase.id})
            return {"success": "good job"}, 200

    @bp.route("/banphrases/toggle/<int:row_id>", methods=["POST"])
    @pajbot.web.utils.requires_level(500)
    def banphrases_toggle(row_id, **options):
        json_data = request.get_json()
        if not json_data:
            return {"error": "No input data provided"}, 400

        try:
            data: ToggleState = ToggleStateSchema().load(json_data)
        except ValidationError as err:
            return {"error": f"Did not match schema: {json.dumps(err.messages)}"}, 400

        with DBManager.create_session_scope() as db_session:
            row = db_session.query(Banphrase).filter_by(id=row_id).one_or_none()

            if not row:
                return {"error": "Banphrase with this ID not found"}, 404

            row.enabled = data.new_state
            db_session.commit()
            payload = {"id": row.id, "new_state": data.new_state}
            AdminLogManager.post(
                "Banphrase toggled", options["user"], "Enabled" if data.new_state else "Disabled", row.id, row.phrase
            )
            SocketClientManager.send("banphrase.update", payload)
            return {"success": "successful toggle", "new_state": data.new_state}

    @bp.route("/banphrases/test", methods=["POST"])
    def banphrases_test():
        if request.is_json:
            # Example request:
            # curl -XPOST -d'{"message": "xD"}' -H'Content-Type: application/json' http://localhost:7070/api/v1/banphrases/test
            json_data = request.get_json()
            if not json_data:
                return {"error": "Missing json body"}, 400
            try:
                data: TestBanphrase = TestBanphraseSchema().load(json_data)
            except ValidationError as err:
                return {"error": f"Did not match schema: {json.dumps(err.messages)}"}, 400
        else:
            # This endpoint must handle form requests
            # Example requests:
            # curl -XPOST -H 'Content-Type: application/x-www-form-urlencoded' -d 'message=xD2' http://localhost:7070/api/v1/banphrases/test
            # curl -XPOST -F 'message=xD2' http://localhost:7070/api/v1/banphrases/test
            try:
                data: TestBanphrase = TestBanphraseSchema().load(request.form.to_dict())
            except ValidationError as err:
                return {"error": f"Did not match schema: {json.dumps(err.messages)}"}, 400

        message = data.message

        if not message:
            return {"error": "Parameter `message` cannot be empty."}, 400

        ret = {"banned": False, "input_message": message}

        banphrase_manager = BanphraseManager(None).load()
        try:
            res = banphrase_manager.check_message(message, None)
        finally:
            banphrase_manager.db_session.close()

        if res is not False:
            ret["banned"] = True
            ret["banphrase_data"] = res.jsonify()

        return ret

    # @bp.route("/banphrases/dump")
    # def banphrases_dump():
    #     banphrase_manager = BanphraseManager(None).load()
    #     try:
    #         payload = {"banphrases": []}
    #         for bp in banphrase_manager.enabled_banphrases:
    #             payload["banphrases"].append(bp.jsonify())

    #         return payload, 200
    #     except:
    #         log.exception("Error getting enabled banphrases")
    #         return {"error": "hmm"}, 500
    #     finally:
    #         banphrase_manager.db_session.close()

import logging

import pajbot.modules
import pajbot.utils
import pajbot.web.utils
from pajbot.managers.adminlog import AdminLogManager
from pajbot.managers.db import DBManager
from pajbot.models.banphrase import Banphrase, BanphraseManager
from pajbot.models.sock import SocketClientManager

from flask_restful import Resource, reqparse

log = logging.getLogger(__name__)


class APIBanphraseRemove(Resource):
    @pajbot.web.utils.requires_level(500)
    def post(self, banphrase_id, **options):
        with DBManager.create_session_scope() as db_session:
            banphrase = db_session.query(Banphrase).filter_by(id=banphrase_id).one_or_none()
            if banphrase is None:
                return {"error": "Invalid banphrase ID"}, 404
            AdminLogManager.post("Banphrase removed", options["user"], banphrase.id, banphrase.phrase)
            db_session.delete(banphrase)
            db_session.delete(banphrase.data)
            SocketClientManager.send("banphrase.remove", {"id": banphrase.id})
            return {"success": "good job"}, 200


class APIBanphraseToggle(Resource):
    def __init__(self):
        super().__init__()

        self.post_parser = reqparse.RequestParser()
        self.post_parser.add_argument("new_state", required=True)

    @pajbot.web.utils.requires_level(500)
    def post(self, row_id, **options):
        args = self.post_parser.parse_args()

        try:
            new_state = int(args["new_state"])
        except (ValueError, KeyError):
            return {"error": "Invalid `new_state` parameter."}, 400

        with DBManager.create_session_scope() as db_session:
            row = db_session.query(Banphrase).filter_by(id=row_id).one_or_none()

            if not row:
                return {"error": "Banphrase with this ID not found"}, 404

            row.enabled = new_state == 1
            db_session.commit()
            payload = {"id": row.id, "new_state": row.enabled}
            AdminLogManager.post(
                "Banphrase toggled", options["user"], "Enabled" if row.enabled else "Disabled", row.id, row.phrase
            )
            SocketClientManager.send("banphrase.update", payload)
            return {"success": "successful toggle", "new_state": new_state}


class APIBanphraseTest(Resource):
    def __init__(self):
        super().__init__()

        self.post_parser = reqparse.RequestParser()
        self.post_parser.add_argument("message", required=True)

    def post(self, **options):
        args = self.post_parser.parse_args()

        try:
            message = str(args["message"])
        except (ValueError, KeyError):
            return {"error": "Invalid `message` parameter."}, 400

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
            ret["banphrase_data"] = res

        return ret


class APIBanphraseDump(Resource):
    def __init__(self):
        super().__init__()

    @staticmethod
    def get(**options):
        banphrase_manager = BanphraseManager(None).load()
        try:
            return banphrase_manager.enabled_banphrases
        finally:
            banphrase_manager.db_session.close()


def init(api):
    api.add_resource(APIBanphraseRemove, "/banphrases/remove/<int:banphrase_id>")
    api.add_resource(APIBanphraseToggle, "/banphrases/toggle/<int:row_id>")

    # Test a message against banphrases
    api.add_resource(APIBanphraseTest, "/banphrases/test")

    # Dump
    # api.add_resource(APIBanphraseDump, '/banphrases/dump')

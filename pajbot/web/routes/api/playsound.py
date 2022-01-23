from pajbot.managers.adminlog import AdminLogManager
from pajbot.managers.db import DBManager
from pajbot.models.playsound import Playsound
from pajbot.models.sock import SocketClientManager
from pajbot.modules import PlaysoundModule
from pajbot.web.utils import requires_level

from flask_restful import Resource
from flask_restful.reqparse import RequestParser


class PlaysoundAPI(Resource):
    @requires_level(500)
    def put(self, playsound_name, **options):
        playsound_name = PlaysoundModule.massage_name(playsound_name)

        if not PlaysoundModule.validate_name(playsound_name):
            return (
                {
                    "error": "Invalid Playsound name. The playsound name may only contain lowercase latin letters, 0-9, -, or _. No spaces :rage:"
                },
                400,
            )

        post_parser = RequestParser()
        post_parser.add_argument("link", required=True)
        args = post_parser.parse_args()

        try:
            link = args["link"]
        except (ValueError, KeyError):
            return {"error": "Invalid `link` parameter."}, 400

        with DBManager.create_session_scope() as db_session:
            count = db_session.query(Playsound).filter(Playsound.name == playsound_name).count()
            if count >= 1:
                return "Playsound already exists", 400

            # the rest of the parameters are initialized with defaults
            playsound = Playsound(name=playsound_name, link=link)
            db_session.add(playsound)
            log_msg = f"The {playsound_name} playsound has been added"
            AdminLogManager.add_entry("Playsound added", options["user"], log_msg)

            return "OK", 200

    @requires_level(500)
    def post(self, playsound_name, **options):
        # require JSON so the cooldown can be null
        post_parser = RequestParser()
        post_parser.add_argument("link", required=True)
        post_parser.add_argument("volume", type=int, required=True)
        post_parser.add_argument("cooldown", type=int, required=False)
        post_parser.add_argument("enabled", type=bool, required=False)

        args = post_parser.parse_args()

        link = args["link"]
        if not PlaysoundModule.validate_link(link):
            return "Empty or bad link, links must start with https:// and must not contain spaces", 400

        volume = args["volume"]
        if not PlaysoundModule.validate_volume(volume):
            return "Bad volume argument", 400

        # cooldown is allowed to be null/None
        cooldown = args.get("cooldown", None)
        if not PlaysoundModule.validate_cooldown(cooldown):
            return "Bad cooldown argument", 400

        enabled = args["enabled"]
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

    @requires_level(500)
    def delete(self, playsound_name, **options):
        with DBManager.create_session_scope() as db_session:
            playsound = db_session.query(Playsound).filter(Playsound.name == playsound_name).one_or_none()

            if playsound is None:
                return "Playsound does not exist", 404

            log_msg = f"The {playsound.name} playsound has been removed"
            AdminLogManager.add_entry("Playsound removed", options["user"], log_msg)
            db_session.delete(playsound)

            return "OK", 200


class PlayPlaysoundAPI(Resource):
    @requires_level(500)
    def post(self, playsound_name, **options):
        with DBManager.create_session_scope() as db_session:
            count = db_session.query(Playsound).filter(Playsound.name == playsound_name).count()

            if count <= 0:
                return "Playsound does not exist", 404
            # explicitly don't check for disabled

        SocketClientManager.send("playsound.play", {"name": playsound_name})

        return "OK", 200


def init(api):
    api.add_resource(PlaysoundAPI, "/playsound/<playsound_name>")
    api.add_resource(PlayPlaysoundAPI, "/playsound/<playsound_name>/play")

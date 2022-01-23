from pajbot.managers.db import DBManager
from pajbot.models.user import User

from flask import request
from flask_restful import Resource


class APIUser(Resource):
    @staticmethod
    def get(login):
        # add ?user_input=true to query user more fuzzily
        query_by_user_input = request.args.get("user_input") == "true"

        with DBManager.create_session_scope() as db_session:
            if query_by_user_input:
                user = User.find_by_user_input(db_session, login)
            else:
                user = User.find_by_login(db_session, login)
            if user is None:
                return {"error": "Not found"}, 404

            # these are provided for legacy purposes - so we don't break the API interface.
            json = user.jsonify()
            json["username_raw"] = json["name"]
            json["username"] = json["login"]
            json["nl_rank"] = json["num_lines_rank"]
            json["minutes_in_chat_online"] = int(json["time_in_chat_online"] / 60)
            json["minutes_in_chat_offline"] = int(json["time_in_chat_offline"] / 60)
            return json


class APIUserByID(Resource):
    @staticmethod
    def get(id):
        with DBManager.create_session_scope() as db_session:
            user = User.find_by_id(db_session, id)
            if user is None:
                return {"error": "Not found"}, 404

            # the aliases like above are not needed here since this API endpoint is new since version 1.38
            return user.jsonify()


def init(api):
    api.add_resource(APIUser, "/users/<login>")
    api.add_resource(APIUserByID, "/users/id/<id>")

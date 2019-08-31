from flask_restful import Resource

from pajbot.managers.user import UserManager


class APIUser(Resource):
    @staticmethod
    def get(username):
        user = UserManager.find_static(username)
        if not user:
            return {"error": "Not found"}, 404

        return user.jsonify()


def init(api):
    api.add_resource(APIUser, "/users/<username>")

from flask import redirect
from flask_restful import Resource

import pajbot.web.utils


class APITest(Resource):
    @staticmethod
    def get():
        return redirect("/commands", 303)


def init(api):
    pajbot.web.utils.init_json_serializer(api)

    api.add_resource(APITest, "/test")

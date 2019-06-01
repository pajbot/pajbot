import json

from flask_restful import Resource
from flask_restful import reqparse

import pajbot.modules
import pajbot.utils
import pajbot.web.utils
from pajbot.managers.redis import RedisManager
from pajbot.streamhelper import StreamHelper


class APICLRDonationsSave(Resource):
    def __init__(self):
        super().__init__()

        self.post_parser = reqparse.RequestParser()
        self.post_parser.add_argument("name", trim=True, required=True)
        self.post_parser.add_argument("streamtip_client_id", trim=True, required=True)
        self.post_parser.add_argument("streamtip_access_token", trim=True, required=True)
        self.post_parser.add_argument("widget_type", trim=True, required=True)
        self.post_parser.add_argument("widget_width", type=int, required=True)
        self.post_parser.add_argument("widget_height", type=int, required=True)
        self.post_parser.add_argument("custom_css", trim=True, required=True)
        self.post_parser.add_argument("tts", trim=True, required=True)

        # Default styles
        self.post_parser.add_argument("styles", trim=True, required=True)

        # Conditions
        self.post_parser.add_argument("conditions", trim=True, required=True)

    @pajbot.web.utils.requires_level(1500)
    def post(self, widget_id, **options):
        args = self.post_parser.parse_args()

        # special case for boolean values
        args["tts"] = args["tts"] == "true"

        # parse json from these string values
        args["styles"] = json.loads(args["styles"])
        args["conditions"] = json.loads(args["conditions"])

        streamer = StreamHelper.get_streamer()
        key = "{streamer}:clr:donations".format(streamer=streamer)
        redis = RedisManager.get()
        redis.hset(key, widget_id, json.dumps(args))

        return {"message": "GOT EM"}, 200


def init(api):
    api.add_resource(APICLRDonationsSave, "/clr/donations/<widget_id>/save")

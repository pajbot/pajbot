from flask_restful import Resource
from flask_restful import reqparse

import pajbot.modules
import pajbot.web.utils  # NOQA
from pajbot.managers.redis import RedisManager
from pajbot.streamhelper import StreamHelper


class APISocialSet(Resource):
    def __init__(self):
        super().__init__()

        self.post_parser = reqparse.RequestParser()
        self.post_parser.add_argument("value", trim=True, required=True)

    @pajbot.web.utils.requires_level(500)
    def post(self, social_key, **options):
        args = self.post_parser.parse_args()

        streamer = StreamHelper.get_streamer()

        if social_key not in StreamHelper.valid_social_keys:
            return {"error": "invalid social key"}, 400

        # TODO key by streamer ID?
        key = f"{streamer}:{social_key}"
        redis = RedisManager.get()

        if len(args["value"]) == 0:
            redis.hdel("streamer_info", key)
        else:
            redis.hset("streamer_info", key, args["value"])

        return {"message": "success!"}, 200


def init(api):
    api.add_resource(APISocialSet, "/social/<social_key>/set")

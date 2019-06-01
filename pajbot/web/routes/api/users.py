from flask_restful import Resource

from pajbot.managers.redis import RedisManager
from pajbot.managers.user import UserManager
from pajbot.streamhelper import StreamHelper


class APIUser(Resource):
    @staticmethod
    def get(username):
        user = UserManager.find_static(username)
        if not user:
            return {"error": "Not found"}, 404

        redis = RedisManager.get()
        key = "{streamer}:users:num_lines".format(streamer=StreamHelper.get_streamer())
        rank = redis.zrevrank(key, user.username)
        if rank is None:
            rank = redis.zcard(key)
        else:
            rank = rank + 1

        return user.jsonify()


def init(api):
    api.add_resource(APIUser, "/users/<username>")

import json

from flask_restful import Resource
from flask_restful import reqparse

import pajbot.modules
import pajbot.web.utils  # NOQA
from pajbot.managers.redis import RedisManager
from pajbot.streamhelper import StreamHelper


class APIEmailTags(Resource):
    def __init__(self):
        super().__init__()

        self.get_parser = reqparse.RequestParser()
        self.get_parser.add_argument("email", trim=True, required=True, location="args")

        self.post_parser = reqparse.RequestParser()
        self.post_parser.add_argument("email", trim=True, required=True)
        self.post_parser.add_argument("tag", trim=True, required=True)

        self.delete_parser = reqparse.RequestParser()
        self.delete_parser.add_argument("email", trim=True, required=True)
        self.delete_parser.add_argument("tag", trim=True, required=True)

    # @pajbot.web.utils.requires_level(500)
    def get(self, **options):
        args = self.get_parser.parse_args()

        email = args["email"].lower()
        streamer = StreamHelper.get_streamer()

        key = "{streamer}:email_tags".format(streamer=streamer)
        redis = RedisManager.get()

        tags_str = redis.hget(key, email)

        payload = {}

        if tags_str is None:
            tags = []
        else:
            tags = json.loads(tags_str)

        payload["tags"] = tags

        return payload

    # @pajbot.web.utils.requires_level(500)
    def post(self, **options):
        # Add a single tag to the email
        args = self.post_parser.parse_args()

        email = args["email"].lower()
        new_tag = args["tag"].lower()
        if len(new_tag) == 0:
            return {"message": "The tag must be at least 1 character long."}, 400
        streamer = StreamHelper.get_streamer()

        key = "{streamer}:email_tags".format(streamer=streamer)
        redis = RedisManager.get()

        tags_str = redis.hget(key, email)

        if tags_str is None:
            tags = []
        else:
            tags = json.loads(tags_str)

        # Is the tag already active?
        if new_tag in tags:
            return {"message": "This tag is already set on the email."}, 409

        tags.append(new_tag)

        redis.hset(key, email, json.dumps(tags))

        return {"message": "Successfully added the tag {} to {}".format(new_tag, email)}

    # @pajbot.web.utils.requires_level(500)
    def delete(self, **options):
        # Add a single tag to the email
        args = self.delete_parser.parse_args()

        email = args["email"].lower()
        new_tag = args["tag"].lower()
        streamer = StreamHelper.get_streamer()

        key = "{streamer}:email_tags".format(streamer=streamer)
        redis = RedisManager.get()

        tags_str = redis.hget(key, email)

        if tags_str is None:
            tags = []
        else:
            tags = json.loads(tags_str)

        # Is the tag already active?
        if new_tag not in tags:
            return {"message": "This tag is not set on the email."}, 409

        tags.remove(new_tag)

        if tags:
            redis.hset(key, email, json.dumps(tags))
        else:
            redis.hdel(key, email)

        return {"message": "Successfully removed the tag {} from {}".format(new_tag, email)}


def init(api):
    api.add_resource(APIEmailTags, "/email/tags")

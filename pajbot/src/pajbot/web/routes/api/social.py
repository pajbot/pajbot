import json
from dataclasses import dataclass

import pajbot.modules
import pajbot.web.utils  # NOQA
from pajbot.managers.redis import RedisManager
from pajbot.streamhelper import StreamHelper

import marshmallow_dataclass
from flask import Blueprint, request
from flask.typing import ResponseReturnValue
from marshmallow import ValidationError


@dataclass
class SocialSet:
    value: str


SocialSetSchema = marshmallow_dataclass.class_schema(SocialSet)


def init(bp: Blueprint) -> None:
    @bp.route("/social/<social_key>/set", methods=["POST"])
    @pajbot.web.utils.requires_level(500)
    def social_set(social_key: str, **options) -> ResponseReturnValue:
        try:
            json_data = request.get_json()
            if not json_data:
                return {"error": "Missing json body"}, 400
            data: SocialSet = SocialSetSchema().load(json_data)
        except ValidationError as err:
            return {"error": f"Did not match schema: {json.dumps(err.messages)}"}, 400

        streamer = StreamHelper.get_streamer()

        if social_key not in StreamHelper.valid_social_keys:
            return {"error": "invalid social key"}, 400

        # TODO key by streamer ID?
        key = f"{streamer}:{social_key}"
        redis = RedisManager.get()

        if len(data.value) == 0:
            redis.hdel("streamer_info", key)
        else:
            redis.hset("streamer_info", key, data.value)

        return {"message": "success!"}, 200

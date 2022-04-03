import json
import logging
from dataclasses import dataclass

from pajbot.managers.db import DBManager
from pajbot.models.sock import SocketClientManager
from pajbot.models.twitter import TwitterUser
from pajbot.web.schemas.pagination import Pagination, PaginationSchema
from pajbot.web.utils import requires_level

import marshmallow_dataclass
from flask import Blueprint, request
from flask.typing import ResponseReturnValue
from marshmallow import ValidationError

log = logging.getLogger(__name__)


@dataclass
class UserRequest:
    username: str


UserRequestSchema = marshmallow_dataclass.class_schema(UserRequest)


def init(bp: Blueprint) -> None:
    @bp.route("/twitter/follows")
    @requires_level(500)
    def twitter_follows_get(**options) -> ResponseReturnValue:
        try:
            data: Pagination = PaginationSchema().load(request.args.to_dict())
        except ValidationError as err:
            return {"error": f"Did not match schema: {json.dumps(err.messages)}"}, 400

        log.info(f"Data: {data}")

        offset = max(0, data.offset)
        limit = max(1, data.limit)

        if data.direction == "desc":
            direction = TwitterUser.id.desc()
        else:
            direction = TwitterUser.id.asc()

        with DBManager.create_session_scope() as db_session:
            return (
                {
                    "_total": db_session.query(TwitterUser).count(),
                    "follows": [
                        t.jsonify() for t in db_session.query(TwitterUser).order_by(direction)[offset : offset + limit]
                    ],
                },
                200,
            )

    @bp.route("/twitter/unfollow", methods=["POST"])
    @requires_level(1000)
    def twitter_unfollow(**options):
        json_data = request.get_json()
        if not json_data:
            return {"error": "No input data provided"}, 400

        try:
            data: UserRequest = UserRequestSchema().load(json_data)
        except ValidationError as err:
            return {"error": f"Did not match schema: {json.dumps(err.messages)}"}, 400

        username = data.username.strip()

        if not username:
            return {"message": "username must contain at least 1 character"}, 400

        with DBManager.create_session_scope() as db_session:
            twitter_user = db_session.query(TwitterUser).filter_by(username=username).one_or_none()
            if twitter_user is None:
                return {"message": "We are not following a twitter user by that name."}, 404

            db_session.delete(twitter_user)
            db_session.flush()
            db_session.commit()

            SocketClientManager.send("twitter.unfollow", {"username": username})

            return {"message": f"Successfully unfollowed {username}"}, 200

    @bp.route("/twitter/follow", methods=["POST"])
    @requires_level(1000)
    def twitter_follow(**options):
        json_data = request.get_json()
        if not json_data:
            return {"error": "No input data provided"}, 400

        try:
            data: UserRequest = UserRequestSchema().load(json_data)
        except ValidationError as err:
            return {"error": f"Did not match schema: {json.dumps(err.messages)}"}, 400

        username = data.username.strip()

        if not username:
            return {"message": "username must contain at least 1 character"}, 400

        with DBManager.create_session_scope() as db_session:
            twitter_user = db_session.query(TwitterUser).filter_by(username=username).one_or_none()
            if twitter_user is not None:
                return {"message": f"We are already following {username}"}, 409

            twitter_user = TwitterUser(username)

            db_session.add(twitter_user)
            db_session.flush()
            db_session.commit()

            SocketClientManager.send("twitter.follow", {"username": username})

            return {"message": f"Successfully followed {username}"}, 200

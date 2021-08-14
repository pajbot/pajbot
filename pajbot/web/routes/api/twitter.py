from flask_restful import Resource
from flask_restful import reqparse

from pajbot.managers.db import DBManager
from pajbot.models.sock import SocketClientManager
from pajbot.models.twitter import TwitterUser
from pajbot.web.utils import requires_level


class APITwitterFollows(Resource):
    def __init__(self):
        super().__init__()
        self.get_parser = reqparse.RequestParser()
        self.get_parser.add_argument("offset", required=False, type=int, default=0, location="args")
        self.get_parser.add_argument("limit", required=False, type=int, default=30, location="args")
        self.get_parser.add_argument("direction", required=False, default="asc", location="args")

    @requires_level(500)
    def get(self, **options):
        args = self.get_parser.parse_args()
        offset = max(0, args["offset"])
        limit = max(1, args["limit"])
        if args["direction"] == "desc":
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


class APITwitterUnfollow(Resource):
    def __init__(self):
        super().__init__()
        self.post_parser = reqparse.RequestParser()
        self.post_parser.add_argument("username", required=True, trim=True)

    @requires_level(1000)
    def post(self, **options):
        args = self.post_parser.parse_args()
        with DBManager.create_session_scope() as db_session:
            twitter_user = db_session.query(TwitterUser).filter_by(username=args["username"]).one_or_none()
            if twitter_user is None:
                return {"message": "We are not following a twitter user by that name."}, 404

            db_session.delete(twitter_user)
            db_session.flush()
            db_session.commit()

            SocketClientManager.send("twitter.unfollow", {"username": args["username"]})

            return {"message": f"Successfully unfollowed {args['username']}"}, 200


class APITwitterFollow(Resource):
    def __init__(self):
        super().__init__()
        self.post_parser = reqparse.RequestParser()
        self.post_parser.add_argument("username", required=True, trim=True)

    @requires_level(1000)
    def post(self, **options):
        args = self.post_parser.parse_args()
        twitter_username = args["username"].lower()

        if len(twitter_username) == 0:
            return {"message": "username must contain at least 1 character"}, 400

        with DBManager.create_session_scope() as db_session:
            twitter_user = db_session.query(TwitterUser).filter_by(username=twitter_username).one_or_none()
            if twitter_user is not None:
                return {"message": f"We are already following {args['username']}"}, 409

            twitter_user = TwitterUser(twitter_username)

            db_session.add(twitter_user)
            db_session.flush()
            db_session.commit()

            SocketClientManager.send("twitter.follow", {"username": twitter_username})

            return {"message": f"Successfully followed {args['username']}"}, 200


def init(api):
    api.add_resource(APITwitterFollows, "/twitter/follows")
    api.add_resource(APITwitterUnfollow, "/twitter/unfollow")
    api.add_resource(APITwitterFollow, "/twitter/follow")

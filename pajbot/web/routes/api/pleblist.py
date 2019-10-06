import logging

from flask import abort
from flask import url_for
from flask_restful import Resource
from flask_restful import reqparse
from sqlalchemy import and_
from sqlalchemy import func
from sqlalchemy.orm import noload

import pajbot.web.utils
from pajbot import utils
from pajbot.managers.db import DBManager
from pajbot.models.pleblist import PleblistManager
from pajbot.models.pleblist import PleblistSong
from pajbot.models.pleblist import PleblistSongInfo
from pajbot.models.stream import Stream
from pajbot.web import app

log = logging.getLogger(__name__)


class APIPleblistSkip(Resource):
    def __init__(self):
        super().__init__()

        self.post_parser = reqparse.RequestParser()
        self.post_parser.add_argument("password", required=True, location="cookies")

    def post(self, song_id, **options):
        args = self.post_parser.parse_args()

        try:
            pajbot.web.utils.pleblist_login(args["password"], app.bot_config)
        except pajbot.exc.InvalidLogin as e:
            return {"error": str(e)}, 401

        with DBManager.create_session_scope() as db_session:
            song = db_session.query(PleblistSong).options(noload("*")).filter_by(id=song_id).one_or_none()
            if song is None:
                abort(404)

            db_session.delete(song)
            db_session.flush()

            return {"message": "GOT EM"}, 200


class APIPleblistListCurrent(Resource):
    def get(self):
        with DBManager.create_session_scope() as session:
            current_stream = session.query(Stream).filter_by(ended=False).order_by(Stream.stream_start).first()
            if current_stream is None:
                return {"error": "Stream offline"}, 400

            songs = session.query(PleblistSong).filter(
                PleblistSong.stream_id == current_stream.id, PleblistSong.date_played.is_(None)
            )

            return pajbot.web.utils.jsonify_list("songs", songs, base_url=url_for(self.endpoint, _external=True))


class APIPleblistListStream(Resource):
    def get(self, stream_id):
        with DBManager.create_session_scope() as session:
            songs = session.query(PleblistSong).filter_by(stream_id=stream_id)

            return pajbot.web.utils.jsonify_list(
                "songs", songs, base_url=url_for(self.endpoint, stream_id=stream_id, _external=True)
            )


class APIPleblistListAfter(Resource):
    def get(self, song_id):
        with DBManager.create_session_scope() as session:
            current_stream = session.query(Stream).filter_by(ended=False).order_by(Stream.stream_start).first()
            if current_stream is None:
                return {"error": "Stream offline"}, 400

            songs = session.query(PleblistSong).filter(
                and_(
                    PleblistSong.stream_id == current_stream.id,
                    PleblistSong.date_played.is_(None),
                    PleblistSong.id > song_id,
                )
            )

            return pajbot.web.utils.jsonify_list(
                "songs", songs, base_url=url_for(self.endpoint, song_id=song_id, _external=True)
            )


class APIPleblistAdd(Resource):
    def __init__(self):
        super().__init__()

        self.post_parser = reqparse.RequestParser()
        self.post_parser.add_argument("youtube_id", trim=True, required=True)
        self.post_parser.add_argument("password", trim=True, required=True)
        self.post_parser.add_argument("skip_after", type=int, default=None, required=False)

    def post(self):
        args = self.post_parser.parse_args()

        try:
            pajbot.web.utils.pleblist_login(args["password"], app.bot_config)
        except pajbot.exc.InvalidLogin as e:
            return {"error": str(e)}, 401

        with DBManager.create_session_scope() as session:
            youtube_id = args["youtube_id"]
            current_stream = session.query(Stream).filter_by(ended=False).order_by(Stream.stream_start).first()
            if current_stream is None:
                return {"error": "Stream offline"}, 400

            skip_after = args["skip_after"]

            log.info(f"Request song youtube ID: {youtube_id}")
            song_requested = PleblistSong(current_stream.id, youtube_id, skip_after=skip_after)
            session.add(song_requested)
            song_info = session.query(PleblistSongInfo).filter_by(pleblist_song_youtube_id=youtube_id).first()
            if song_info is None and song_requested.song_info is None:
                PleblistManager.init(app.bot_config["youtube"]["developer_key"])
                song_info = PleblistManager.create_pleblist_song_info(song_requested.youtube_id)
                if song_info is not False:
                    session.add(song_info)
                    session.commit()

            return {"success": "got em!"}, 200


class APIPleblistNext(Resource):
    def __init__(self):
        super().__init__()

        self.post_parser = reqparse.RequestParser()
        self.post_parser.add_argument("song_id", type=int, required=True)
        self.post_parser.add_argument("password", trim=True, required=True)

    def post(self):
        args = self.post_parser.parse_args()

        try:
            pajbot.web.utils.pleblist_login(args["password"], app.bot_config)
        except pajbot.exc.InvalidLogin as e:
            return {"error": str(e)}, 401

        with DBManager.create_session_scope() as session:
            try:
                current_song = (
                    session.query(PleblistSong)
                    .filter(PleblistSong.id == args["song_id"])
                    .order_by(PleblistSong.date_added.asc())
                    .first()
                )
            except ValueError:
                return {"error": "Invalid data song_id"}, 400

            if current_song is None:
                return {"error": "No song active in the pleblist"}, 404

            current_song.date_played = utils.now()
            session.commit()

            # TODO: Add more data.
            # Was this song forcefully skipped? Or did it end naturally.

            return {"success": "got em!"}, 200


class APIPleblistValidate(Resource):
    def __init__(self):
        super().__init__()

        self.post_parser = reqparse.RequestParser()
        self.post_parser.add_argument("youtube_id", trim=True, required=True)

    def post(self):
        args = self.post_parser.parse_args()

        with DBManager.create_session_scope() as session:
            youtube_id = args["youtube_id"]
            log.info(f"Validating youtube ID {youtube_id}")
            song_info = session.query(PleblistSongInfo).filter_by(pleblist_song_youtube_id=youtube_id).first()
            if song_info is not None:
                return {"message": "success", "song_info": song_info.jsonify()}

            PleblistManager.init(app.bot_config["youtube"]["developer_key"])
            song_info = PleblistManager.create_pleblist_song_info(youtube_id)
            if not song_info and len(youtube_id) > 11:
                youtube_id = youtube_id[:11]
                song_info = session.query(PleblistSongInfo).filter_by(pleblist_song_youtube_id=youtube_id).first()
                if song_info is not None:
                    return {"message": "success", "new_youtube_id": youtube_id, "song_info": song_info.jsonify()}
                else:
                    song_info = PleblistManager.create_pleblist_song_info(youtube_id)

            if song_info:
                log.debug(song_info)
                session.add(song_info)
                session.commit()
                return {"message": "success", "new_youtube_id": youtube_id, "song_info": song_info.jsonify()}

            return {"message": "invalid youtube id", "song_info": None}


class APIPleblistBlacklist(Resource):
    @staticmethod
    def get():
        with DBManager.create_session_scope() as session:
            current_stream = session.query(Stream).filter_by(ended=False).order_by(Stream.stream_start).first()
            if current_stream is None:
                return {"error": "Stream offline"}, 400

            # TODO: implement this

            return {"error": "NOT IMPLEMENTED"}, 400

            # return jsonify({'success': True})


def jsonify_query(query):
    return [PleblistSongTop(v[0], v[1]).jsonify() for v in query]


class PleblistSongTop:
    def __init__(self, song, count):
        self.song = song
        self.count = count

    def jsonify(self):
        payload = self.song.jsonify()
        payload["count"] = self.count
        return payload


class APIPleblistTop(Resource):
    def get(self):
        with DBManager.create_session_scope() as session:
            # songs = session.query(PleblistSong, func.count(PleblistSong.song_info).label('total')).group_by(PleblistSong.youtube_id).order_by('total DESC')
            songs = (
                session.query(PleblistSong, func.count(PleblistSong.youtube_id).label("total"))
                .group_by(PleblistSong.youtube_id)
                .order_by("total DESC")
            )

            log.info(songs)
            log.info(songs.all())

            return pajbot.web.utils.jsonify_list(
                "songs",
                songs,
                default_limit=50,
                max_limit=500,
                base_url=url_for(self.endpoint, _external=True),
                jsonify_method=jsonify_query,
            )


class APIPleblistCheck(Resource):
    def __init__(self):
        super().__init__()

        self.post_parser = reqparse.RequestParser()
        self.post_parser.add_argument("password", required=True, location="cookies")

    def get(self):
        args = self.post_parser.parse_args()

        try:
            pajbot.web.utils.pleblist_login(args["password"], app.bot_config)
        except pajbot.exc.InvalidLogin as e:
            return {"error": str(e)}, 401

        return {"success": True}


def init(api):
    api.add_resource(APIPleblistSkip, "/pleblist/skip/<int:song_id>")
    api.add_resource(APIPleblistListCurrent, "/pleblist/list")
    api.add_resource(APIPleblistListStream, "/pleblist/list/<stream_id>")
    api.add_resource(APIPleblistListAfter, "/pleblist/list/after/<song_id>")
    api.add_resource(APIPleblistAdd, "/pleblist/add")
    api.add_resource(APIPleblistNext, "/pleblist/next")
    api.add_resource(APIPleblistValidate, "/pleblist/validate")
    api.add_resource(APIPleblistBlacklist, "/pleblist/blacklist")
    api.add_resource(APIPleblistTop, "/pleblist/top")
    api.add_resource(APIPleblistCheck, "/pleblist/check")

import logging
import time

from flask import redirect
from flask import session
from flask import render_template

from pajbot.managers.db import DBManager
from pajbot.models.stream import Stream
from pajbot.utils import find
from pajbot.web.utils import seconds_to_vodtime
from pajbot.web.utils import requires_level

log = logging.getLogger(__name__)


def init(app):
    @app.route("/songrequest/")
    @requires_level(500, "/songrequest")
    def songrequest(**options):
        if session.get("twitch_token_expire", 0) <= round(time.time()):
            return redirect("/login?n=/songrequest")
        return render_template("songrequest.html", token_access=session.get("twitch_token"))

    # @app.route("/songrequest/history/")
    # def songrequest_history():
    #     with DBManager.create_session_scope() as session:

    #         q = session.query(PleblistSong).order_by(PleblistSong.id.asc())
    #         songs = []
    #         queue = []
    #         queue_index = 1
    #         queue_time = 0
    #         playing_now = None
    #         for song in q:
    #             if song.song_info is None:
    #                 continue

    #             data = {"song_duration": song.song_info.duration if song.skip_after is None else song.skip_after}

    #             if song.date_played is None:
    #                 # Song has not been played
    #                 # Figure out when it will be played~
    #                 data["queue_index"] = queue_index
    #                 data["queue_time"] = queue_time
    #                 queue_index = queue_index + 1
    #                 queue_time = queue_time + data["song_duration"]
    #                 queue.append((data, song))
    #             elif song.date_played is not None and song.date_finished is None:
    #                 # Song is playing
    #                 data["queue_index"] = 0
    #                 data["queue_time"] = 0
    #                 queue_index = queue_index + 1
    #                 queue_time = queue_time + data["song_duration"]
    #                 playing_now = (data, song)
    #             else:
    #                 songs.append((data, song))

    #         total_length_left = sum(
    #             [
    #                 song.skip_after or song.song_info.duration
    #                 if song.date_played is None and song.song_info is not None
    #                 else 0
    #                 for _, song in songs
    #             ]
    #         )
    #         current_stream = session.query(Stream).filter_by(ended=False).order_by(Stream.stream_start.desc()).first()
    #         live = current_stream is not None
    #         queue.reverse()
    #         songs = songs + queue
    #         if playing_now is not None:
    #             songs.append(playing_now)
    #         songs.reverse()
    #         return render_template(
    #             "pleblist_history.html",
    #             songs=songs,
    #             live=live,
    #             total_length_left=total_length_left,
    #         )

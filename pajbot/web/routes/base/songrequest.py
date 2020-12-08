import logging

from flask import render_template

from pajbot.managers.db import DBManager
from pajbot.managers.songrequest_queue_manager import SongRequestQueueManager
from pajbot.models.songrequest import SongrequestQueue, SongrequestHistory
from pajbot.modules import SongrequestModule

log = logging.getLogger(__name__)


def init(app):
    @app.route("/songrequest")
    def songrequest():
        with DBManager.create_session_scope() as db_session:
            playing_in = 0
            track_number = 1
            songs_queue = []
            SongRequestQueueManager.force_reload()
            current_song = SongrequestQueue.get_current_song(db_session)
            queue = ([current_song] if current_song else []) + SongrequestQueue.get_playlist(
                db_session, 49 if current_song else 50, False
            )

            if len(queue) < 50 and SongrequestModule.module_settings()["use_backup_playlist"]:
                queue += SongrequestQueue.get_backup_playlist(db_session, 50 - len(queue), False)

            for song in queue:
                if song.song_info is None:
                    continue
                jsonify = song.webjsonify()
                m, s = divmod(playing_in, 60)
                m = int(m)
                s = int(s)
                jsonify["playing_in"] = (
                    (f"{m:02d}:{s:02d}" if playing_in != 0 else "Currently playing")
                    if current_song
                    else "Song Request Closed"
                )
                jsonify["track_number"] = track_number
                playing_in += song.time_left
                track_number += 1
                songs_queue.append(jsonify)

            history = (
                db_session.query(SongrequestHistory)
                .filter(SongrequestHistory.song_info.has(banned=False))
                .order_by(SongrequestHistory.id.desc())
                .limit(50)
                .all()
            )
            track_number = 1
            songs_history = []
            for song in history:
                if song.song_info.banned:
                    continue
                jsonify = song.webjsonify()
                jsonify["track_number"] = track_number
                track_number += 1
                songs_history.append(jsonify)

            return render_template(
                "songrequest.html",
                songs_queue=songs_queue if SongrequestModule.is_enabled() else [],
                songs_history=songs_history,
            )

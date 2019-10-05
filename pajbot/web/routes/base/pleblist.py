import logging

from flask import redirect
from flask import render_template

from pajbot.managers.db import DBManager
from pajbot.models.pleblist import PleblistSong
from pajbot.models.stream import Stream
from pajbot.models.stream import StreamChunk
from pajbot.utils import find
from pajbot.web.utils import seconds_to_vodtime

log = logging.getLogger(__name__)


def init(app):
    @app.route("/pleblist/")
    def pleblist():
        return render_template("pleblist.html")

    @app.route("/pleblist/host/")
    def pleblist_host():
        return render_template(
            "pleblist_host.html",
            has_streamtip=False,
            streamtip_client_id="",
            has_streamlabs=False,
            streamlabs_client_id="",
            has_streamelements=False,
        )

    @app.route("/pleblist/history/")
    def pleblist_history_redirect():
        with DBManager.create_session_scope() as session:
            current_stream = session.query(Stream).filter_by(ended=False).order_by(Stream.stream_start.desc()).first()
            if current_stream is not None:
                return redirect(f"/pleblist/history/{current_stream.id}/", 303)

            last_stream = session.query(Stream).filter_by(ended=True).order_by(Stream.stream_start.desc()).first()
            if last_stream is not None:
                return redirect(f"/pleblist/history/{last_stream.id}/", 303)

            return render_template("pleblist_history_no_stream.html"), 404

    @app.route("/pleblist/history/<int:stream_id>/")
    def pleblist_history_stream(stream_id):
        with DBManager.create_session_scope() as session:
            stream = session.query(Stream).filter_by(id=stream_id).one_or_none()
            if stream is None:
                return render_template("pleblist_history_404.html"), 404

            previous_stream = session.query(Stream).filter_by(id=stream_id - 1).one_or_none()
            next_stream = session.query(Stream).filter_by(id=stream_id + 1).one_or_none()

            # Fetch all associated stream chunks so we can associate songs to a certain stream chunk
            stream_chunks = session.query(StreamChunk).filter(StreamChunk.stream_id == stream.id).all()

            q = session.query(PleblistSong).filter(PleblistSong.stream_id == stream.id).order_by(PleblistSong.id.asc())
            songs = []
            queue_index = 0
            queue_time = 0
            for song in q:
                if song.song_info is None:
                    continue

                data = {"song_duration": song.song_info.duration if song.skip_after is None else song.skip_after}

                if song.date_played is None:
                    # Song has not been played
                    # Figure out when it will be played~
                    data["queue_index"] = queue_index
                    data["queue_time"] = queue_time
                    queue_index = queue_index + 1
                    queue_time = queue_time + data["song_duration"]
                else:
                    # Song has already been played
                    # Figure out a link to the vod URL
                    stream_chunk = find(
                        lambda stream_chunk: stream_chunk.chunk_start <= song.date_played
                        and (stream_chunk.chunk_end is None or stream_chunk.chunk_end >= song.date_played),
                        stream_chunks,
                    )
                    if stream_chunk is not None:
                        vodtime_in_seconds = (song.date_played - stream_chunk.chunk_start).total_seconds() - data[
                            "song_duration"
                        ]
                        data["vod_url"] = f"{stream_chunk.video_url}?t={seconds_to_vodtime(vodtime_in_seconds)}"

                songs.append((data, song))

            total_length_left = sum(
                [
                    song.skip_after or song.song_info.duration
                    if song.date_played is None and song.song_info is not None
                    else 0
                    for _, song in songs
                ]
            )

            first_unplayed_song = find(lambda song: song[1].date_played is None, songs)

            return render_template(
                "pleblist_history.html",
                stream=stream,
                previous_stream=previous_stream,
                next_stream=next_stream,
                songs=songs,
                total_length_left=total_length_left,
                first_unplayed_song=first_unplayed_song,
                stream_chunks=stream_chunks,
            )

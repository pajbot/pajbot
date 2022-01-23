import logging
import urllib

from pajbot.managers.db import DBManager
from pajbot.managers.schedule import ScheduleManager
from pajbot.models.command import Command
from pajbot.models.pleblist import PleblistManager, PleblistSong
from pajbot.modules import BaseModule, ModuleSetting
from pajbot.streamhelper import StreamHelper

from sqlalchemy import func

log = logging.getLogger(__name__)


def find_youtube_id_in_string(string):
    if len(string) < 11:
        # Too short to be a youtube ID
        return False

    if len(string) == 11:
        # Assume it's a straight up youtube ID
        return string

    if not (string.lower().startswith("http://") or string.lower().startswith("https://")):
        string = "http://" + string

    urldata = urllib.parse.urlparse(string)

    if urldata.netloc == "youtu.be":
        youtube_id = urldata.path[1:]
    elif urldata.netloc.endswith("youtube.com"):
        qs = urllib.parse.parse_qs(urldata.query)
        if "v" not in qs:
            return False
        youtube_id = qs["v"][0]
    else:
        return False

    return youtube_id


class PleblistModule(BaseModule):
    ID = __name__.split(".")[-1]
    NAME = "Song Requests"
    DESCRIPTION = ""
    CATEGORY = "Feature"
    HIDDEN = True
    SETTINGS = [
        ModuleSetting(
            key="songrequest_command",
            label="Allow song requests through chat",
            type="boolean",
            required=True,
            default=False,
        ),
        ModuleSetting(
            key="max_song_length",
            label="Max song length (in seconds)",
            type="number",
            required=True,
            placeholder="Max song length (in seconds)",
            default=360,
            constraints={"min_value": 1, "max_value": 3600},
        ),
        ModuleSetting(
            key="max_songs_per_user",
            label="# song requests active per user",
            type="number",
            required=True,
            default=2,
            constraints={"min_value": 1, "max_value": 3600},
        ),
        ModuleSetting(
            key="point_cost",
            label="Point costs for requesting a song",
            type="number",
            required=True,
            default=500,
            constraints={"min_value": 0, "max_value": 1000000},
        ),
    ]

    def bg_pleblist_add_song(self, stream_id, youtube_id, force, bot, source):
        with DBManager.create_session_scope() as db_session:
            song_info = PleblistManager.get_song_info(youtube_id, db_session)
            if song_info is None or force:
                try:
                    PleblistManager.init(bot.config["youtube"]["developer_key"])
                except:
                    log.error("No youtube key set up.")
                    bot.whisper(source, "No youtube key set up")
                    return False

                song_info = PleblistManager.create_pleblist_song_info(youtube_id)
                if song_info is False:
                    bot.whisper(source, "Invalid song given (or the YouTube API is down)")
                    return False

                db_session.merge(song_info)
                db_session.commit()

            # See if the user has already submitted X songs
            num_unplayed_songs_requested = int(
                db_session.query(func.count(PleblistSong.id))
                .filter_by(stream_id=stream_id, user_id=source.id, date_played=None)
                .one()[0]
            )
            if num_unplayed_songs_requested >= self.settings["max_songs_per_user"] and not force:
                bot.whisper(source, f"You can only request {num_unplayed_songs_requested} songs at the same time!")
                return False

            # Add the song request
            song_request = PleblistSong(bot.stream_manager.current_stream.id, youtube_id, user_id=source.id)

            # See if the song is too long
            # If it is, make it autoskip after that time
            if song_info.duration > self.settings["max_song_length"]:
                song_request.skip_after = self.settings["max_song_length"]

            db_session.add(song_request)

            bot.say(f'{source} just requested the song "{song_info.title}" to be played KKona')

    def pleblist_add_song(self, bot, source, message, **rest):
        if not message:
            return False

        # 1. Find youtube ID in message
        msg_split = message.split(" ")
        youtube_id = find_youtube_id_in_string(msg_split[0])

        force = False

        try:
            if msg_split[1] == "force" and source.level >= 500:
                force = True
        except:
            pass

        if youtube_id is False:
            bot.whisper(source, "Could not find a valid youtube ID in your argument.")
            return False

        # 2. Make sure the stream is live
        stream_id = StreamHelper.get_current_stream_id()
        if stream_id is None or stream_id is False:
            bot.whisper(source, "You cannot request songs while the stream is offline.")
            return False

        ScheduleManager.execute_now(self.bg_pleblist_add_song, args=[stream_id, youtube_id, force, bot, source])

    def load_commands(self, **options):
        if self.settings["songrequest_command"]:
            self.commands["songrequest"] = Command.raw_command(
                self.pleblist_add_song,
                delay_all=0,
                delay_user=3,
                notify_on_error=True,
                cost=self.settings["point_cost"],
            )

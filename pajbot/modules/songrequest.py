import logging
import urllib
import urllib.request
import urllib.parse
import re
import json
import random

from sqlalchemy import func

from pajbot.managers.db import DBManager
from pajbot.managers.handler import HandlerManager
from pajbot.managers.schedule import ScheduleManager
from pajbot.models.command import Command
from pajbot.models.songrequest import SongrequestQueue
from pajbot.models.songrequest import SongRequestSongInfo
from pajbot.models.user import User
from pajbot.modules import BaseModule
from pajbot.modules import ModuleSetting
from pajbot.streamhelper import StreamHelper

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


def find_youtube_video_by_search(search):
    try:
        query_string = urllib.parse.urlencode({"search_query": search})
        html_content = urllib.request.urlopen("http://www.youtube.com/results?" + query_string)
        return re.findall(r"href=\"\/watch\?v=(.{11})", html_content.read().decode())[0]
    except:
        return None


class SongrequestModule(BaseModule):
    ID = __name__.split(".")[-1]
    NAME = "Songrequest"
    DESCRIPTION = "Request Songs"
    CATEGORY = "Feature"
    SETTINGS = [
        ModuleSetting(key="youtube_key", label="Youtube developer key", type="text", required=True, default="",),
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
            key="point_cost",
            label="Point costs for requesting a song",
            type="number",
            required=True,
            default=500,
            constraints={"min_value": 0, "max_value": 250000},
        ),
        ModuleSetting(
            key="backup_playlist_id",
            label="Songs to play when no song is being requested backup playlist id",
            type="text",
            required=True,
            default="",
        ),
        ModuleSetting(
            key="volume",
            label="Default volume for song requests",
            type="number",
            required=True,
            default=100,
            constraints={"min_value": 0, "max_value": 100},
        ),
        ModuleSetting(
            key="volume_multiplier",
            label="Volume multiplier",
            type="number",
            required=True,
            default="100",
            constraints={"min_value": 0, "max_value": 100},
        ),
        ModuleSetting(
            key="use_spotify",
            label="Checks Spotify for current song if no song is playing",
            type="boolean",
            required=True,
            default=True,
        ),
        ModuleSetting(
            key="send_message_in_chat",
            label="Send a message in chat upon a song request",
            type="boolean",
            required=True,
            default=True,
        ),
        ModuleSetting(
            key="message_in_chat",
            label="Message sent in chat after someone requests a song {username} is the requestor, {title} is the song title, {current_pos} is the current queue position, {playing_in} is how long until the song is played",
            type="text",
            required=True,
            default='{username} just requested the song "{title}" to be played KKona',
        ),
        ModuleSetting(
            key="message_in_chat_no_songs_playing",
            label="Message sent when no songs are playing",
            type="text",
            required=True,
            default="No songs are currently playing",
        ),
        ModuleSetting(
            key="message_in_chat_when_song_is_playing",
            label="Message sent when a song is playing, {title} is the title of the song, {requestor} is the person who requested, {time_left} is the time left for playing",
            type="text",
            required=True,
            default="The current song is {title} requested by {requestor}",
        ),
        ModuleSetting(
            key="message_in_chat_when_song_is_playing_spotify",
            label="Message sent when a song is playing, {title} is the title of the song, {requestor} is the person who requested, {time_left} is the time left for playing",
            type="text",
            required=True,
            default="The current song is {title} by {artists}",
        ),
        ModuleSetting(
            key="message_in_chat_when_next_song",
            label="Message sent when a next song is requested, {title} is the title of the song, {requestor} is the person who requested, {time_till} is the time left for playing",
            type="text",
            required=True,
            default="The next song is {title} requested by {requestor}",
        ),
        ModuleSetting(
            key="message_in_chat_when_next_song_none",
            label="Message sent when a next song is requested but there isn't one",
            type="text",
            required=True,
            default="There are no songs currently queued",
        ),
        ModuleSetting(
            key="send_message_on_open",
            label="Message sent when a next song is requested but there isn't one",
            type="boolean",
            required=True,
            default=True,
        ),
        ModuleSetting(
            key="message_sent_on_open",
            label="Message sent when a next song is requested but there isn't one",
            type="text",
            required=True,
            default="Song Request has been opened!",
        ),
        ModuleSetting(
            key="send_message_on_close",
            label="Message sent when a next song is requested but there isn't one",
            type="boolean",
            required=True,
            default=True,
        ),
        ModuleSetting(
            key="message_sent_on_close",
            label="Message sent when a next song is requested but there isn't one",
            type="text",
            required=True,
            default="Song Request has been closed!",
        ),
    ]

    def getBackUpListSongs(self, next_page=None):
        songs = []
        urlin = (
            f"https://www.googleapis.com/youtube/v3/playlistItems?part=snippet&maxResults=50&playlistId={self.settings['backup_playlist_id']}&key={self.settings['youtube_key']}"
            + (f"&pageToken={next_page}" if next_page else "")
        )
        with urllib.request.urlopen(urlin) as url:
            data = json.loads(url.read().decode())
            for song in data["items"]:
                songs.append(song["snippet"]["resourceId"]["videoId"])
            try:
                next_page = data["nextPageToken"]
                return songs + self.getBackUpListSongs(next_page)
            except:
                return songs

    def create_song_request_queue(self, video_id, bot, source):
        with DBManager.create_session_scope() as db_session:
            song_info = SongRequestSongInfo._create_or_get(db_session, video_id, self.youtube)
            if not song_info:
                log.error("There was an error!")
                return False
            skip_after = (
                self.settings["max_song_length"] if song_info.duration > self.settings["max_song_length"] else None
            )
            songrequest_queue = SongrequestQueue._create(db_session, video_id, skip_after, source.login)
            db_session.commit()
            m, s = divmod(int(songrequest_queue.playing_in(db_session)), 60)
            playing_in = f"{m:02d}:{s:02d}"
            if self.settings["send_message_in_chat"]:
                bot.say(
                    self.settings["message_in_chat"].format(
                        username=source.username_raw,
                        title=song_info.title,
                        current_pos=songrequest_queue.queue
                        + (1 if SongrequestQueue._get_current_song(db_session) else 0),
                        playing_in=playing_in,
                    )
                )
        self.bot.songrequest_manager._playlist()
        return True

    def add_song(self, bot, source, message, **rest):
        if not message:
            self.bot.whisper(source, "Could not find a valid youtube ID in your argument.")
            return False
        # 1. Find youtube ID in message
        msg_split = message.split(" ")
        youtube_id = find_youtube_id_in_string(msg_split[0])

        if youtube_id is False:
            youtube_id = find_youtube_video_by_search(message)
            if youtube_id is None:
                self.bot.whisper(source, "Could not find a valid youtube ID in your argument.")
                return False

        # 2. Make sure the stream is live
        stream_id = StreamHelper.get_current_stream_id()
        if stream_id is None or stream_id is False:
            self.bot.whisper(source, "You cannot request songs while the stream is offline.")
            return False

        return self.create_song_request_queue(youtube_id, bot, source)

    def get_current_song(self, bot, source, message, **rest):
        with DBManager.create_session_scope() as db_session:
            current_song = SongrequestQueue._get_current_song(db_session)
            if current_song:
                if current_song.requestor:
                    requestor = User.find_by_login(db_session, current_song.requestor)
                    if requestor:
                        bot.say(
                            self.settings["message_in_chat_when_song_is_playing"].format(
                                title=current_song.song_info(db_session).title,
                                requestor=requestor.username_raw,
                                time_left=current_song.time_left(db_session),
                            )
                        )
                        return True
                bot.say(
                    self.settings["message_in_chat_when_song_is_playing"].format(
                        title=current_song.song_info(db_session).title,
                        requestor="Backup Playlist",
                        time_left=current_song.time_left(db_session),
                    )
                )
                return True
            if self.settings["use_spotify"]:
                is_playing, title, artistsArr = bot.spotify_api.state(bot.spotify_token_manager)
                if is_playing:
                    bot.say(
                        self.settings["message_in_chat_when_song_is_playing_spotify"].format(
                            title=title, artists=", ".join([str(artist) for artist in artistsArr])
                        )
                    )
                    return True
        bot.say(self.settings["message_in_chat_no_songs_playing"])
        return True

    def get_next_song(self, bot, source, message, **rest):
        with DBManager.create_session_scope() as db_session:
            next_song = SongrequestQueue._get_next_song(db_session)
            if next_song:
                if next_song.requestor:
                    requestor = User.find_by_login(db_session, next_song.requestor)
                    if requestor:
                        bot.say(
                            self.settings["message_in_chat_when_next_song"].format(
                                title=next_song.song_info(db_session).title,
                                requestor=requestor.username_raw,
                                time_left=next_song.time_left(db_session),
                            )
                        )
                        return True
                bot.say(
                    self.settings["message_in_chat_when_next_song"].format(
                        title=next_song.song_info(db_session).title,
                        requestor="Backup Playlist",
                        time_left=next_song.time_left(db_session),
                    )
                )
                return True
        bot.say(self.settings["message_in_chat_when_next_song_none"])
        return True

    def open_module(self, bot, source, message, **rest):
        if self.bot.songrequest_manager.open_module_function():
            if self.settings["send_message_on_open"]:
                bot.whisper(source, self.settings["message_sent_on_open"])
                bot.say(self.settings["message_sent_on_open"])
                return
        bot.whisper(source, "Song request is already open!")

    def close_module(self, bot, source, message, **rest):
        if self.bot.songrequest_manager.close_module_function():
            if self.settings["send_message_on_open"]:
                bot.whisper(source, self.settings["message_sent_on_close"])
                bot.say(self.settings["message_sent_on_close"])
                return
        bot.whisper(source, "Song request is already closed!")

    def skip(self, bot, source, message, **rest):
        if self.bot.songrequest_manager.skip_function(source.login):
            bot.whisper(source, "Song has been skipped!")
            return
        bot.whisper(source, "No song is playing!")

    def pause(self, bot, source, message, **rest):
        if self.bot.songrequest_manager.pause_function():
            bot.whisper(source, "Song has been paused")
            return
        bot.whisper(source, "Song is already paused!")

    def resume(self, bot, source, message, **rest):
        if self.bot.songrequest_manager.resume_function():
            bot.whisper(source, "Song has been resumed")
            return
        bot.whisper(source, "Song is already playing!")

    def volume(self, bot, source, message, **rest):
        if not message:
            bot.say(
                f"The current volume is {int(self.bot.songrequest_manager.volume*100*(1/(self.settings['volume_multiplier']/100)))}%"
            )
            return True
        try:
            val = int(message)
            if val < 0 or val > 100:
                bot.whisper(source, "Invalid volume setting enter a volume between 0-100")
                return False
        except:
            bot.whisper(source, "Invalid volume setting enter a volume between 0-100")
            return False
        self.bot.songrequest_manager.volume_function(val / 100)
        bot.whisper(source, "Volume has been changed to " + message + "%")
        return True

    def show_video(self, bot, source, message, **rest):
        if self.bot.songrequest_manager.show_function():
            bot.whisper(source, "The video has been shown!")
            return True
        bot.whisper(source, "The video is already showing!")
        return True

    def hide_video(self, bot, source, message, **rest):
        if self.bot.songrequest_manager.hide_function():
            bot.whisper(source, "The video has been hidden!")
            return True
        bot.whisper(source, "The video is already hidden!")
        return True

    def load_commands(self, **options):
        self.commands["sr"] = self.commands["songrequest"] = Command.raw_command(
            self.add_song, delay_all=0, delay_user=3, notify_on_error=True, cost=self.settings["point_cost"],
        )
        self.commands["song"] = Command.raw_command(
            self.get_current_song, delay_all=0, delay_user=3, notify_on_error=True,
        )
        self.commands["next"] = Command.raw_command(
            self.get_next_song, delay_all=0, delay_user=3, notify_on_error=True,
        )
        self.commands["opensr"] = Command.raw_command(
            self.open_module, delay_all=0, delay_user=3, level=500, notify_on_error=True,
        )
        self.commands["closesr"] = Command.raw_command(
            self.close_module, delay_all=0, delay_user=3, level=500, notify_on_error=True,
        )
        self.commands["skip"] = Command.raw_command(
            self.skip, delay_all=0, delay_user=3, level=500, notify_on_error=True,
        )
        self.commands["pause"] = Command.raw_command(
            self.pause, delay_all=0, delay_user=3, level=500, notify_on_error=True,
        )
        self.commands["resume"] = Command.raw_command(
            self.resume, delay_all=0, delay_user=3, level=500, notify_on_error=True,
        )
        self.commands["volume"] = Command.raw_command(
            self.volume, delay_all=0, delay_user=3, level=500, notify_on_error=True,
        )
        self.commands["showvideo"] = Command.raw_command(
            self.show_video, delay_all=0, delay_user=3, level=500, notify_on_error=True,
        )
        self.commands["hidevideo"] = Command.raw_command(
            self.hide_video, delay_all=0, delay_user=3, level=500, notify_on_error=True,
        )

    def enable(self, bot):
        if not self.bot:
            return

        import apiclient
        from apiclient.discovery import build

        def build_request(_, *args, **kwargs):
            import httplib2

            new_http = httplib2.Http()
            return apiclient.http.HttpRequest(new_http, *args, **kwargs)

        self.youtube = build("youtube", "v3", developerKey=self.settings["youtube_key"], requestBuilder=build_request)

        with DBManager.create_session_scope() as db_session:
            SongrequestQueue._clear_backup_songs(db_session)
            if self.settings["backup_playlist_id"] and self.settings["backup_playlist_id"] is not "":
                backup_songs = self.getBackUpListSongs()
                random.shuffle(backup_songs)
                SongrequestQueue._load_backup_songs(db_session, backup_songs, self.youtube, self.settings)
            db_session.commit()
        SongrequestQueue._update_queue()
        self.bot.songrequest_manager.enable(self.settings, self.youtube)
        HandlerManager.add_handler("on_stream_stop", self.bot.songrequest_manager.close_module_function)

    def disable(self, bot):
        if not self.bot:
            return
        self.bot.songrequest_manager.disable()
        self.bot.songrequest_manager.disable()
        HandlerManager.remove_handler("on_stream_stop", self.bot.songrequest_manager.close_module_function)

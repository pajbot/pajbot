import logging
import urllib
import json
import random

import urllib.request
import urllib.parse
import regex as re

from pajbot.models.songrequest import SongrequestQueue, SongRequestSongInfo, SongrequestHistory
from pajbot.models.user import User
from pajbot.managers.songrequest_queue_manager import SongRequestQueueManager
from pajbot.managers.schedule import ScheduleManager
from pajbot.managers.db import DBManager
from pajbot.exc import (
    ManagerDisabled,
    InvalidState,
    InvalidVolume,
    InvalidSong,
    UserNotFound,
    InvalidPlaylist,
    SongBanned,
)
from pajbot import utils

log = logging.getLogger("pajbot")

WIDGET_ID = 4
VOLUME_MULTIPLIER = 0.4


def find_youtube_id_in_string(string):
    if len(string) < 11:
        # Too short to be a youtube ID
        return False

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


def find_youtube_video_by_search(search, run_int=0):
    try:
        query_string = urllib.parse.urlencode({"search_query": search})
        html_content = urllib.request.urlopen("http://www.youtube.com/results?" + query_string)
        return re.findall(r"href=\"\/watch\?v=(.{11})", html_content.read().decode())[0]
    except:
        if run_int < 3:
            return find_youtube_video_by_search(search, run_int=run_int + 1)
        return None


def find_backup_playlist_id(search):
    try:
        return re.findall(r"[&?]list=([^&]+)", search)[0]
    except:
        return None


class SongrequestManager:
    def __init__(self, bot, youtube_api_key):
        self.bot = bot
        self.spotify_playing = False
        self.video_showing = False
        self.previous_queue = 0
        self.volume = 0
        self.max_song_length = 0
        self.youtube_api_key = youtube_api_key
        self.backup_play_list_id = None

        self.states = self.default_states

        self.db_session = DBManager.create_session()
        self.current_song = None
        current_song = SongrequestQueue.get_current_song(self.db_session)
        if current_song:
            SongrequestQueue.create(
                self.db_session, current_song.video_id, current_song.skip_after, current_song.requested_by_id, 0
            )
            SongRequestQueueManager.update_song_playing_id("")
            current_song.purge(self.db_session)
            self.db_session.commit()

        import apiclient
        from apiclient.discovery import build

        def build_request(_, *args, **kwargs):
            import httplib2

            new_http = httplib2.Http()
            return apiclient.http.HttpRequest(new_http, *args, **kwargs)

        self.youtube = build("youtube", "v3", developerKey=self.youtube_api_key, requestBuilder=build_request)
        self.module = None
        self.auto_skip_schedule = None
        self.auto_skip_salt = None
        self.ready = False

    def disable(self):
        self.states = self.default_states
        self._module_state()
        if self.current_song:
            SongrequestQueue.create(
                self.db_session,
                self.current_song.video_id,
                self.current_song.skip_after,
                self.current_song.requested_by_id,
                0,
            )
            SongRequestQueueManager.update_song_playing_id("")
            self.current_song.purge(self.db_session)
            self.db_session.commit()
        self.load_song()

    def load(self, module):
        self.module = None
        self.volume_function(module.settings["volume"])
        self.max_song_length_function(module.settings["max_song_length"])
        self.use_spotify_state_function(module.settings["use_spotify"])
        self.backup_playlist_state_function(module.settings["use_backup_playlist"])
        try:
            self.set_backup_playlist(module.settings["backup_playlist_id"])
        except InvalidPlaylist:
            settings = module.settings
            settings["backup_playlist_id"] = ""
            module.update_settings(**settings)
        self.module = module

    @property
    def default_states(self):
        return {
            "enabled": False,
            "requests_open": False,
            "auto_play": False,
            "backup_playlist": False,
            "paused": False,
            "use_spotify": False,
            "show_video": False,
            "play_on_stream": False,
        }

    def set_backup_playlist(self, backup_play_list_id):
        if not self.states["enabled"]:
            raise ManagerDisabled()

        SongrequestQueue.clear_backup_songs(self.db_session)
        if backup_play_list_id:
            backup_songs = self._get_backup_playlist_songs(backup_play_list_id)
            if not backup_songs:
                raise InvalidPlaylist()

            random.shuffle(backup_songs)
            SongrequestQueue.load_backup_songs(self.db_session, backup_songs, self.youtube)
        self.backup_play_list_id = backup_play_list_id
        if self.module:
            settings = self.module.settings
            settings["backup_playlist_id"] = self.backup_play_list_id
            self.module.update_settings(**settings)
        self.db_session.commit()
        self._backup_playlist()
        self._module_state()

    def state(self, state, value):
        if state not in self.states or not isinstance(value, bool):
            raise InvalidState("Sate is not valid")
        self.states[state] = value
        self._module_state()

    def ready_function(self):
        if self.ready:
            return

        self.resume_function()

    def _auto_skip(self, salt):
        if salt != self.auto_skip_salt:
            return

        self.skip_function()

    def pause_function(self):
        if not self.states["enabled"]:
            raise ManagerDisabled()

        self.current_song.played_for += (utils.now() - self.current_song.date_resumed).total_seconds()
        self.current_song.date_resumed = None
        self.db_session.commit()

        self.state("paused", True)
        try:
            self.auto_skip_schedule.remove()
        except:
            pass
        self.auto_skip_salt = None
        self._pause()

    def resume_function(self):
        if not self.states["enabled"]:
            raise ManagerDisabled()

        self.current_song.date_resumed = utils.now()
        self.db_session.commit()

        self.state("paused", False)
        self.auto_skip_salt = utils.salt_gen()
        self.auto_skip_schedule = ScheduleManager.execute_delayed(
            self.current_song.time_left, self._auto_skip, args=[self.auto_skip_salt]
        )
        self._resume()

    def show_function(self):
        if not self.states["enabled"]:
            raise ManagerDisabled()

        self.state("show_video", True)
        self._show()

    def hide_function(self):
        if not self.states["enabled"]:
            raise ManagerDisabled()

        self.state("show_video", False)
        self._hide()

    def ban_function(self, database_id=None, hist_database_id=None, songinfo_database_id=None):
        if not self.states["enabled"]:
            raise ManagerDisabled()

        if not songinfo_database_id and not database_id and not hist_database_id:
            raise InvalidSong()

        if database_id:
            song = SongrequestQueue.from_id(self.db_session, int(database_id))
            song_info = song.song_info if song else None
        elif songinfo_database_id:
            song_info = SongRequestSongInfo.get(self.db_session, songinfo_database_id)
        else:
            song = SongrequestHistory.from_id(self.db_session, int(hist_database_id))
            song_info = song.song_info if song else None

        if not song_info:
            raise InvalidSong()

        if song_info.banned:
            return

        song_info.banned = True
        SongrequestQueue.pruge_videos(self.db_session, song_info.video_id)
        self.db_session.commit()

        if self.current_song and self.current_song.song_info == song_info:
            self.load_song()
            self._update_current_song()

        self._playlist()
        self._backup_playlist()
        self._playlist_history()
        self._favourite_list()
        self._banned_list()

    def unban_function(self, database_id=None, hist_database_id=None, songinfo_database_id=None):
        if not self.states["enabled"]:
            raise ManagerDisabled()

        if not songinfo_database_id and not database_id and not hist_database_id:
            raise InvalidSong()

        if database_id:
            song = SongrequestQueue.from_id(self.db_session, int(database_id))
            song_info = song.song_info
        elif songinfo_database_id:
            song_info = SongRequestSongInfo.get(self.db_session, songinfo_database_id)
        else:
            song = SongrequestHistory.from_id(self.db_session, int(hist_database_id))
            song_info = song.song_info if song else None

        if not song_info:
            raise InvalidSong()

        if not song_info.banned:
            return

        song_info.banned = False
        self.db_session.commit()

        self._playlist()
        self._backup_playlist()
        self._playlist_history()
        self._favourite_list()
        self._banned_list()

    def remove_function(self, database_id):
        if not self.states["enabled"]:
            raise ManagerDisabled()

        song = SongrequestQueue.from_id(self.db_session, database_id)
        if not song:
            raise InvalidSong()
        playing = song.playing

        song.purge(self.db_session)
        self.db_session.commit()

        self._playlist()

        if playing:
            self.bot.songrequest_manager.load_song()

    def request_function(
        self,
        requested_by,
        video_id=None,
        database_id=None,
        hist_database_id=None,
        songinfo_database_id=None,
        queue=None,
    ):
        if not self.states["enabled"]:
            raise ManagerDisabled()

        requested_by = User.find_by_user_input(self.db_session, requested_by)
        if not requested_by:
            raise UserNotFound()

        requested_by_id = requested_by.id
        if video_id:
            song_info = SongRequestSongInfo.create_or_get(self.db_session, video_id, self.youtube)
        elif database_id:
            song = SongrequestQueue.from_id(self.db_session, int(database_id))
            song_info = song.song_info
        elif songinfo_database_id:
            song_info = SongRequestSongInfo.get(self.db_session, songinfo_database_id)
        else:
            song = SongrequestHistory.from_id(self.db_session, int(hist_database_id))
            song_info = song.song_info

        if not song_info:
            raise InvalidSong()

        if song_info.banned:
            raise SongBanned()

        skip_after = self.max_song_length if song_info.duration > self.max_song_length else None
        song = SongrequestQueue.create(self.db_session, song_info.video_id, skip_after, requested_by_id)
        if queue:
            song.move_song(queue)
        self.db_session.commit()
        if not self.current_song or not self.current_song.requested_by:
            self.load_song()

        self._playlist()
        self._favourite_list()
        self._playlist_history()
        return song

    def skip_function(self, skipped_by=None):
        if not self.states["enabled"]:
            raise ManagerDisabled()

        if not self.current_song:
            raise InvalidSong()

        if skipped_by:
            skipped_by = User.find_by_user_input(self.db_session, skipped_by)
            if not skipped_by:
                raise UserNotFound()

        self.load_song(skipped_by.id if skipped_by else None)

    def previous_function(self, requested_by):
        if not self.states["enabled"]:
            raise ManagerDisabled()

        requested_by = User.find_by_user_input(self.db_session, requested_by)
        if not requested_by:
            raise UserNotFound()

        requested_by_id = requested_by.id
        SongrequestHistory.insert_previous(self.db_session, requested_by_id, self.previous_queue)
        self.db_session.commit()
        self.previous_queue += 1
        self.load_song(requested_by_id)

    def seek_function(self, _time):
        if not self.states["enabled"]:
            raise ManagerDisabled()

        if not self.current_song:
            raise InvalidSong()

        try:
            self.auto_skip_schedule.remove()
        except:
            pass
        self.current_song.played_for = _time
        self.current_song.date_resumed = None
        self.db_session.commit()
        self._seek(_time)

    def favourite_function(self, database_id=None, hist_database_id=None, songinfo_database_id=None):
        if not self.states["enabled"]:
            raise ManagerDisabled()

        if not songinfo_database_id and not database_id and not hist_database_id:
            raise InvalidSong()

        if database_id:
            song = SongrequestQueue.from_id(self.db_session, int(database_id))
            song_info = song.song_info if song else None
        elif songinfo_database_id:
            song_info = SongRequestSongInfo.get(self.db_session, songinfo_database_id)
        else:
            song = SongrequestHistory.from_id(self.db_session, int(hist_database_id))
            song_info = song.song_info if song else None

        if not song_info:
            raise InvalidSong()

        if song_info.favourite:
            return

        song_info.favourite = True
        self.db_session.commit()
        self._playlist()
        self._backup_playlist()
        self._playlist_history()
        self._favourite_list()
        self._banned_list()
        if self.current_song and self.current_song.song_info == song_info:
            self._update_current_song()

    def unfavourite_function(self, database_id=None, hist_database_id=None, songinfo_database_id=None):
        if not self.states["enabled"]:
            raise ManagerDisabled()

        if not songinfo_database_id and not database_id and not hist_database_id:
            raise InvalidSong()

        if database_id:
            song = SongrequestQueue.from_id(self.db_session, int(database_id))
            song_info = song.song_info if song else None
        elif songinfo_database_id:
            song_info = SongRequestSongInfo.get(self.db_session, songinfo_database_id)
        else:
            song = SongrequestHistory.from_id(self.db_session, int(hist_database_id))
            song_info = song.song_info if song else None

        if not song_info:
            raise InvalidSong()

        if not song_info.favourite:
            return

        song_info.favourite = False
        self.db_session.commit()
        self._playlist()
        self._backup_playlist()
        self._playlist_history()
        self._favourite_list()
        self._banned_list()
        if self.current_song and self.current_song.song_info == song_info:
            self._update_current_song()

    def move_function(self, database_id, to_id):
        if not self.states["enabled"]:
            raise ManagerDisabled()

        song = SongrequestQueue.from_id(self.db_session, database_id)
        if not song:
            raise InvalidSong()

        song.move_song(to_id)
        self.db_session.commit()
        self._playlist()

    def volume_function(self, volume):
        if not self.states["enabled"]:
            raise ManagerDisabled()
        try:
            volume = int(str(volume).replace("%", ""))
            if volume <= 100 and volume >= 0:
                self.volume = volume
                self._volume()
                if self.module:
                    settings = self.module.settings
                    settings["volume"] = self.volume
                    self.module.update_settings(**settings)
            else:
                raise InvalidVolume()
        except:
            raise InvalidVolume()

    def max_song_length_function(self, max_song_length):
        if not self.states["enabled"]:
            raise ManagerDisabled()
        try:
            max_song_length = int(max_song_length)
            if max_song_length >= 0:
                self.max_song_length = max_song_length
                if self.module:
                    settings = self.module.settings
                    settings["max_song_length"] = self.volume
                    self.module.update_settings(**settings)
            else:
                raise ValueError
        except:
            raise ValueError

    def auto_play_state_function(self, value):
        if not self.states["enabled"]:
            raise ManagerDisabled()

        self.state("auto_play", value)
        if value and not self.current_song:
            self.load_song()

    def request_state_function(self, value):
        if not self.states["enabled"]:
            raise ManagerDisabled()

        self.state("requests_open", value)
        self.bot.say(f"Song requests have been {'opened' if value else 'closed'}")

    def backup_playlist_state_function(self, value):
        if not self.states["enabled"]:
            raise ManagerDisabled()

        self.state("backup_playlist", value)
        if self.module:
            settings = self.module.settings
            settings["use_backup_playlist"] = "on" if value else "off"
            self.module.update_settings(**settings)

        if value and not self.current_song:
            self.load_song()

    def use_spotify_state_function(self, value):
        if not self.states["enabled"]:
            raise ManagerDisabled()

        self.state("use_spotify", value)
        if self.module:
            settings = self.module.settings
            settings["use_spotify"] = "on" if value else "off"
            self.module.update_settings(**settings)

    def play_on_stream_function(self, value):
        if not self.states["enabled"]:
            raise ManagerDisabled()

        self.state("play_on_stream", value)
        if self.current_song:
            SongrequestQueue.create(
                self.db_session,
                self.current_song.video_id,
                self.current_song.skip_after,
                self.current_song.requested_by_id,
                0,
            )
            SongRequestQueueManager.update_song_playing_id("")
            self.current_song.purge(self.db_session)
            self.db_session.commit()
            self.load_song()

    def load_song(self, skipped_by_id=None):
        if not self.states["enabled"]:
            raise ManagerDisabled()

        if self.current_song:
            if self.current_song.current_song_time > 5:
                self.previous_queue = 0
                histroy = self.current_song.to_histroy(self.db_session, skipped_by_id)
            else:
                self.current_song.purge(self.db_session)
            self.db_session.commit()
            if not self.states["paused"]:
                try:
                    self.auto_skip_schedule.remove()
                except:
                    pass
            self._playlist_history()
            self._stop_video()
        self._hide()
        self.current_song = None
        self.auto_skip_salt = None

        if not self.states["auto_play"]:
            if self.spotify_playing:
                if not self.bot.spotify_player_api:
                    log.warning("Spotify Enabled but not setup!")
                else:
                    self.bot.spotify_player_api.play(self.bot.spotify_token_manager)
                    log.info("Resumed Spotify")
                    self.spotify_playing = False
            return False

        current_song = SongrequestQueue.get_current_song(self.db_session)
        if not current_song:
            current_song = SongrequestQueue.pop_next_song(self.db_session, use_backup=self.states["backup_playlist"])
        if current_song:
            SongRequestQueueManager.update_song_playing_id(current_song.id)
            current_song.played_for = 0
            current_song.date_resumed = utils.now()
            self.current_song = current_song
            self._volume()
            self._play()

            if self.states["use_spotify"]:
                if not self.bot.spotify_player_api:
                    log.warning("Spotify Enabled but not setup!")
                else:
                    is_playing = self.bot.spotify_player_api.state(self.bot.spotify_token_manager)[0]
                    if is_playing:
                        self.bot.spotify_player_api.pause(self.bot.spotify_token_manager)
                        self.spotify_playing = True

            if not current_song.requested_by_id:
                SongrequestQueue.create(
                    self.db_session, current_song.video_id, current_song.skip_after, None, backup=True
                )
            self.db_session.commit()
            if current_song.requested_by_id:
                self._playlist()
            else:
                self._backup_playlist()
            return True

        SongRequestQueueManager.update_song_playing_id("")
        if self.states["use_spotify"]:
            if self.spotify_playing:
                if not self.bot.spotify_player_api:
                    log.warning("Spotify Enabled but not setup!")
                else:
                    self.bot.spotify_player_api.play(self.bot.spotify_token_manager)
                    log.info("Resumed Spotify")
                    self.spotify_playing = False
        if self.video_showing:
            self._hide()
        return False

    def _play(self):
        if self.states["play_on_stream"]:
            self.bot.websocket_manager.emit("songrequest_play", WIDGET_ID, {"video_id": self.current_song.video_id})
            self.state("paused", True)
        self.bot.songrequest_websocket_manager.emit(
            "play", {"current_song": self.current_song.webjsonify(), "current_timestamp": str(utils.now().timestamp())}
        )
        if self.states["show_video"]:
            self._show()

    def _update_current_song(self):
        self.bot.songrequest_websocket_manager.emit(
            "update_current_song", {"current_song": self.current_song.webjsonify() if self.current_song else {}}
        )

    def _pause(self):
        if self.states["play_on_stream"]:
            self.bot.websocket_manager.emit("songrequest_pause", WIDGET_ID, {})
        self._hide()

    def _resume(self):
        if self.states["play_on_stream"]:
            self.bot.websocket_manager.emit("songrequest_resume", WIDGET_ID, {"volume": self.volume})
        if self.states["show_video"]:
            self._show()

    def _volume(self):
        if self.states["play_on_stream"]:
            self.bot.websocket_manager.emit(
                "songrequest_volume", WIDGET_ID, {"volume": self.volume * VOLUME_MULTIPLIER}
            )
        self.bot.songrequest_websocket_manager.emit("volume", {"volume": self.volume})

    def _seek(self, _time):
        if self.states["play_on_stream"]:
            self.bot.websocket_manager.emit(
                "songrequest_seek", WIDGET_ID, {"seek_time": self.current_song.current_song_time}
            )
            self.state("paused", True)
        self.bot.songrequest_websocket_manager.emit(
            "play", {"current_song": self.current_song.webjsonify(), "current_timestamp": str(utils.now().timestamp())}
        )

    def _show(self):
        if self.states["play_on_stream"]:
            self.bot.websocket_manager.emit("songrequest_show", WIDGET_ID, {})
        self.video_showing = True

    def _hide(self):
        self.bot.websocket_manager.emit("songrequest_hide", WIDGET_ID, {})
        self.video_showing = False

    def _playlist(self):
        playlist = SongrequestQueue.get_playlist(self.db_session, 30)
        self.bot.songrequest_websocket_manager.emit("playlist", {"playlist": playlist})

    def _backup_playlist(self):
        playlist = SongrequestQueue.get_backup_playlist(self.db_session, 30)
        self.bot.songrequest_websocket_manager.emit("backup_playlist", {"backup_playlist": playlist})

    def _playlist_history(self):
        self.bot.songrequest_websocket_manager.emit(
            "history_list", {"history_list": SongrequestHistory.get_history(self.db_session, 30)}
        )

    def _favourite_list(self):
        favourite_list = [x.jsonify() for x in SongRequestSongInfo.get_favourite(self.db_session)]
        self.bot.songrequest_websocket_manager.emit("favourite_list", {"favourite_list": favourite_list})

    def _banned_list(self):
        banned_list = [x.jsonify() for x in SongRequestSongInfo.get_banned(self.db_session)]
        self.bot.songrequest_websocket_manager.emit("banned_list", {"banned_list": banned_list})

    def _module_state(self):
        states = self.states
        states["backup_playlist_id"] = self.backup_play_list_id
        self.bot.songrequest_websocket_manager.emit("module_state", {"module_state": states})

    def _stop_video(self):
        self.bot.songrequest_websocket_manager.emit("play", {"current_song": {}})
        self.bot.websocket_manager.emit("songrequest_stop", WIDGET_ID, {})

    def _get_backup_playlist_songs(self, playlist_id, next_page=None):
        songs = []
        urlin = (
            f"https://www.googleapis.com/youtube/v3/playlistItems?part=snippet&maxResults=50&playlistId={playlist_id}&key={self.youtube_api_key}"
            + (f"&pageToken={next_page}" if next_page else "")
        )
        try:
            with urllib.request.urlopen(urlin) as url:
                data = json.loads(url.read().decode())
                for song in data["items"]:
                    songs.append(song["snippet"]["resourceId"]["videoId"])
                try:
                    next_page = data["nextPageToken"]
                    return songs + self._get_backup_playlist_songs(playlist_id, next_page)
                except:
                    return songs
        except:
            return []

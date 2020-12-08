import logging
import datetime

from sqlalchemy import func

from pajbot.managers.handler import HandlerManager
from pajbot.managers.songrequest import find_youtube_id_in_string, find_youtube_video_by_search
from pajbot.managers.songrequest_queue_manager import SongRequestQueueManager
from pajbot.models.songrequest import SongrequestQueue
from pajbot.models.command import Command
from pajbot.modules import BaseModule
from pajbot.modules import ModuleSetting
from pajbot.exc import ManagerDisabled, UserNotFound, InvalidSong, InvalidVolume, SongBanned
from pajbot import utils

log = logging.getLogger(__name__)


class SongrequestModule(BaseModule):
    ID = __name__.split(".")[-1]
    NAME = "Songrequest"
    DESCRIPTION = "Request Songs"
    CATEGORY = "Feature"
    SETTINGS = [
        ModuleSetting(
            key="max_song_length",
            label="Max song length (in seconds)",
            type="number",
            required=True,
            placeholder="Max song length (in seconds)",
            default=360,
            constraints={"min_value": 0, "max_value": 3600},
        ),
        ModuleSetting(
            key="point_cost",
            label="Point costs for requesting a song",
            type="number",
            required=True,
            default=500,
            constraints={"min_value": 0},
        ),
        ModuleSetting(
            key="number_of_votes_for_skip",
            label="Number of votes required to skip a song, 0 for disable",
            type="number",
            required=True,
            default=10,
            constraints={"min_value": 0},
        ),
        ModuleSetting(
            key="max_requests_per_user",
            label="Max requests in the current queue per user",
            type="number",
            required=True,
            default=3,
            constraints={"min_value": 0},
        ),
        ModuleSetting(
            key="backup_playlist_id",
            label="Songs to play when no song is being requested backup playlist id",
            type="text",
            required=False,
            default="",
        ),
        ModuleSetting(
            key="volume",
            label="Default volume for song requests",
            type="number",
            required=True,
            default=10,
            constraints={"min_value": 0, "max_value": 100},
        ),
        ModuleSetting(
            key="use_spotify",
            label="Checks Spotify for current song if no song is playing",
            type="boolean",
            default=False,
        ),
        ModuleSetting(
            key="use_backup_playlist",
            label="Use the backup playlist if no songs are playing | requires a backup playlist to be set",
            type="boolean",
            default=True,
        ),
        ModuleSetting(
            key="send_message_in_chat",
            label="Send a message in chat upon a song request",
            type="boolean",
            default=True,
        ),
        ModuleSetting(
            key="message_in_chat",
            label="Message sent in chat after someone requests a song {user} is the requestor, {title} is the song title, {current_pos} is the current queue position, {playing_in} is how long until the song is played",
            type="text",
            required=True,
            default='{user} just requested the song "{title}" to be played KKona',
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
            label="Message sent when a requested song is playing, {title} is the title of the song, {requestor} is the person who requested, {time_left} is the time left for playing",
            type="text",
            required=True,
            default="The current song is {title} requested by {requestor}",
        ),
        ModuleSetting(
            key="message_in_chat_when_song_is_playing_spotify",
            label="Message sent when a spotify song is playing, {title} is the title of the song, {artists} is the list of artists",
            type="text",
            required=True,
            default="The current song is {title} by {artists}",
        ),
        ModuleSetting(
            key="message_in_chat_when_next_song",
            label="Message sent when a next song is requested, {title} is the title of the song, {requestor} is the person who requested, {playing_in} is when the song will play",
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
    ]

    def __init__(self, bot):
        super().__init__(bot)
        self.current_vote_skip = []
        self.current_song_id = None

    def add_song(self, bot, source, message, **rest):
        if not self.bot.songrequest_manager.states["requests_open"]:
            self.bot.whisper(source, "Song requests are currently disabled!")
            return False

        if not message:
            self.bot.whisper(source, "We couldn't find that song")
            return False

        msg_split = message.split(" ")
        youtube_id = find_youtube_id_in_string(msg_split[0])

        if youtube_id is False:
            youtube_id = find_youtube_video_by_search(message)
            if youtube_id is None:
                self.bot.whisper(source, "We couldn't find that song")
                return False

        if (
            self.settings["max_requests_per_user"]
            < self.bot.songrequest_manager.db_session.query(SongrequestQueue).filter_by(requested_by=source).count()
            and source.level < 500
        ):
            self.bot.whisper(source, "You have reached the max limit for requests, wait till your song plays for more.")
            return False

        try:
            requested_song = self.bot.songrequest_manager.request_function(
                requested_by=source.name, video_id=youtube_id
            )
        except SongBanned:
            self.bot.whisper(source, "That song is currently banned")
            return False

        except InvalidSong:
            self.bot.whisper(source, "We couldn't find that song")
            return False

        except ManagerDisabled:
            self.bot.whisper(source, "The module is disabled")
            return False

        except UserNotFound:
            self.bot.whisper(source, "You are not in our database!")
            return False

        current_pos, playing_in = requested_song.queue_and_playing_in(self.bot.songrequest_manager.db_session)
        if current_pos:
            m, s = divmod(playing_in, 60)
            m = int(m)
            s = int(s)
            playing_in = f"{m:02d}:{s:02d}"
        else:
            playing_in = "now"
        current_pos += 1

        self.bot.say(
            self.settings["message_in_chat"].format(
                user=source, title=requested_song.song_info.title, playing_in=playing_in, current_pos=current_pos,
            )
        )
        return True

    def get_current_song(self, bot, source, message, **rest):
        if self.bot.songrequest_manager.current_song:
            m, s = divmod(self.bot.songrequest_manager.current_song.time_left, 60)
            m = int(m)
            s = int(s)
            time_left = f"{m:02d}:{s:02d}"
            self.bot.say(
                self.settings[
                    "message_in_chat_when_song_is_playing"
                    if self.bot.songrequest_manager.current_song.requested_by
                    else "message_in_chat_when_song_is_playing"
                ].format(
                    title=self.bot.songrequest_manager.current_song.song_info.title,
                    requestor=self.bot.songrequest_manager.current_song.requested_by.name
                    if self.bot.songrequest_manager.current_song.requested_by
                    else "Backup Playlist",
                    time_left=time_left,
                )
            )
            return True

        if self.bot.songrequest_manager.states["use_spotify"] and self.bot.spotify_player_api:
            is_playing, title, artistsArr = self.bot.spotify_player_api.state(self.bot.spotify_token_manager)
            if is_playing:
                self.bot.say(
                    self.settings["message_in_chat_when_song_is_playing_spotify"].format(
                        title=title, artists=", ".join([str(artist) for artist in artistsArr])
                    )
                )
                return True

        self.bot.say(self.settings["message_in_chat_no_songs_playing"])
        return True

    def get_next_song(self, bot, source, message, **rest):
        next_song = SongrequestQueue.get_next_song(self.bot.songrequest_manager.db_session)
        if next_song and not (not self.settings["use_backup_playlist"] and not next_song.requested_by):
            m, s = divmod(next_song.queue_and_playing_in(self.bot.songrequest_manager.db_session)[1], 60)
            m = int(m)
            s = int(s)
            playing_in = f"{m:02d}:{s:02d}"
            self.bot.say(
                self.settings[
                    "message_in_chat_when_next_song" if next_song.requested_by else "message_in_chat_when_next_song"
                ].format(
                    title=next_song.song_info.title,
                    requestor=next_song.requested_by.name if next_song.requested_by else "Backup Playlist",
                    playing_in=playing_in,
                )
            )
            return True

        self.bot.say(self.settings["message_in_chat_when_next_song_none"])
        return True

    def pause(self, bot, source, message, **rest):
        if self.bot.songrequest_manager.states["paused"]:
            self.bot.whisper(source, "The song is already paused")
            return False

        try:
            self.bot.songrequest_manager.pause_function()
        except ManagerDisabled:
            self.bot.whisper(source, "The module is disabled")
            return False

        self.bot.whisper(source, "The video has been paused")
        return True

    def resume(self, bot, source, message, **rest):
        if not self.bot.songrequest_manager.states["paused"]:
            self.bot.whisper(source, "The song is already playing")
            return False

        try:
            self.bot.songrequest_manager.resume_function()
        except ManagerDisabled:
            self.bot.whisper(source, "The module is disabled")
            return False

        self.bot.whisper(source, "The video has been resumed")
        return True

    def skip(self, bot, source, message, **rest):
        if not self.bot.songrequest_manager.current_song:
            self.bot.whisper(source, "No song is currently playing")
            return False

        try:
            self.bot.songrequest_manager.skip_function(source.login)
        except ManagerDisabled:
            self.bot.whisper(source, "The module is disabled")
            return False

        except UserNotFound:
            self.bot.whisper(source, "You are not in our database!")
            return False

        self.bot.whisper(source, "The video has been skipped")
        return True

    def volume(self, bot, source, message, **rest):
        message_split = message.split() if message else []
        if not message_split:
            self.bot.whisper(source, f"The current volume is {self.bot.songrequest_manager.volume}%")
            return True

        try:
            self.bot.songrequest_manager.volume_function(message_split[0])
        except ManagerDisabled:
            self.bot.whisper(source, "The module is disabled")
            return False

        except InvalidVolume:
            self.bot.whisper(source, f"Invalid volume {message_split[0]}")
            return True

        self.bot.whisper(source, f"Volume has been changed to {self.bot.songrequest_manager.volume}%")
        return True

    def show_video(self, bot, source, message, **rest):
        if self.bot.songrequest_manager.states["show_video"]:
            self.bot.whisper(source, "The video is already showing")
            return False

        try:
            self.bot.songrequest_manager.show_function()
        except ManagerDisabled:
            self.bot.whisper(source, "The module is disabled")
            return False

        self.bot.whisper(source, "The video has been shown")
        return True

    def hide_video(self, bot, source, message, **rest):
        if not self.bot.songrequest_manager.states["show_video"]:
            self.bot.whisper(source, "The video is already hidden")
            return False

        try:
            self.bot.songrequest_manager.hide_function()
        except ManagerDisabled:
            self.bot.whisper(source, "The module is disabled")
            return False

        self.bot.whisper(source, "The video has been hidden")
        return True

    def open_requests(self, bot, source, message, **rest):
        if self.bot.songrequest_manager.states["requests_open"]:
            self.bot.whisper(source, "Requests are already open")
            return False

        try:
            self.bot.songrequest_manager.request_state_function(True)
        except ManagerDisabled:
            self.bot.whisper(source, "The module is disabled")
            return False

        self.bot.whisper(source, "Requests have been enabled")
        return True

    def close_requests(self, bot, source, message, **rest):
        if not self.bot.songrequest_manager.states["requests_open"]:
            self.bot.whisper(source, "Requests are already closed")
            return False

        try:
            self.bot.songrequest_manager.request_state_function(False)
        except ManagerDisabled:
            self.bot.whisper(source, "The module is disabled")
            return False

        self.bot.whisper(source, "Requests have been disabled")
        return True

    def enable_auto_play(self, bot, source, message, **rest):
        if self.bot.songrequest_manager.states["auto_play"]:
            self.bot.whisper(source, "Requests are already open")
            return False

        try:
            self.bot.songrequest_manager.auto_play_state_function(True)
        except ManagerDisabled:
            self.bot.whisper(source, "The module is disabled")
            return False

        self.bot.whisper(source, "Auto Play have been enabled")
        return True

    def disable_auto_play(self, bot, source, message, **rest):
        if not self.bot.songrequest_manager.states["auto_play"]:
            self.bot.whisper(source, "Requests are already closed")
            return False

        try:
            self.bot.songrequest_manager.auto_play_state_function(False)
        except ManagerDisabled:
            self.bot.whisper(source, "The module is disabled")
            return False

        self.bot.whisper(source, "Auto Play have been disabled")
        return True

    def blacklist(self, bot, source, message, **rest):
        if not self.bot.songrequest_manager.current_song:
            self.bot.whisper(source, "No song is currently playing")
            return False

        try:
            self.bot.songrequest_manager.ban_function(self.bot.songrequest_manager.current_song.id)
        except ManagerDisabled:
            self.bot.whisper(source, "The module is disabled")
            return False

        self.bot.whisper(source, "That song has been blacklisted")
        return True

    def vote_skip(self, bot, source, message, **rest):
        if not self.settings["number_of_votes_for_skip"]:
            self.bot.whisper(source, "Vote skipping is currently disabled")
            return False

        if not self.bot.songrequest_manager.current_song:
            self.current_vote_skip = []
            self.bot.whisper(source, "No requested song is currently playing")
            return False

        if self.current_song_id != self.bot.songrequest_manager.current_song.id:
            self.current_song_id = self.bot.songrequest_manager.current_song.id
            self.current_vote_skip = []
        if source.id in self.current_vote_skip:
            return False

        self.current_vote_skip.append(source.id)
        if len(self.current_vote_skip) >= self.settings["number_of_votes_for_skip"]:
            try:
                self.bot.songrequest_manager.skip_function()
            except ManagerDisabled:
                self.bot.whisper(source, "The module is disabled")
                return False
            self.bot.say("The song has been skipped")
            return True

        votes_left = self.settings["number_of_votes_for_skip"] - len(self.current_vote_skip)
        self.bot.say(
            f"@{source}, skip requested the current song will be skipped in {votes_left} more vote{'s' if votes_left != 1 else ''}"
        )
        return True

    def when(self, bot, source, message, **rest):
        playlist = SongrequestQueue.get_playlist(self.bot.songrequest_manager.db_session, as_json=False)
        i = 1
        for song in playlist:
            if song.requested_by == source:
                m, s = divmod(song.queue_and_playing_in(self.bot.songrequest_manager.db_session)[1], 60)
                m = int(m)
                s = int(s)
                playing_in = f"in {m:02d}:{s:02d}" if m or s else "next"
                self.bot.say(
                    f'@{source}, your next song "{song.song_info.title}" is currently in position {i} and will be played {playing_in}.'
                )
                return True

            i += 1
        self.bot.say(f"@{source} you currently dont have any songs queued.")
        return True

    def wrong_song(self, bot, source, message, **rest):
        song = (
            self.bot.songrequest_manager.db_session.query(SongrequestQueue)
            .filter_by(requested_by=source)
            .filter(SongrequestQueue.date_added >= utils.now() - datetime.timedelta(seconds=120))
            .order_by(SongrequestQueue.date_added.desc())
            .limit(1)
            .one_or_none()
        )
        if not song:
            self.bot.say(f"@{source} you dont have any songs queued within the last 120 seconds.")
            return False

        if song.current_song_time <= 10:
            self.bot.songrequest_manager.remove_function(song.id)
            source.points += self.settings["point_cost"]
            self.bot.whisper(source, f"Your song has been refunded. You recieved {self.settings['point_cost']} points")
            return True

        self.bot.whisper(source, "Your song has been playing too long for it to be refunded.")
        return False

    def load_commands(self, **options):
        self.commands["sr"] = self.commands["songrequest"] = Command.raw_command(
            self.add_song, delay_all=0, delay_user=3, notify_on_error=True, cost=self.settings["point_cost"]
        )
        self.commands["song"] = Command.raw_command(
            self.get_current_song, delay_all=0, delay_user=3, notify_on_error=True
        )
        self.commands["next"] = Command.raw_command(self.get_next_song, delay_all=0, delay_user=3, notify_on_error=True)
        self.commands["openrequests"] = Command.raw_command(
            self.open_requests, delay_all=0, delay_user=3, level=500, notify_on_error=True
        )
        self.commands["closerequests"] = Command.raw_command(
            self.close_requests, delay_all=0, delay_user=3, level=500, notify_on_error=True
        )
        self.commands["enableautoplay"] = Command.raw_command(
            self.enable_auto_play, delay_all=0, delay_user=3, level=500, notify_on_error=True
        )
        self.commands["disableautoplay"] = Command.raw_command(
            self.disable_auto_play, delay_all=0, delay_user=3, level=500, notify_on_error=True
        )
        self.commands["skip"] = Command.raw_command(
            self.skip, delay_all=0, delay_user=0, level=500, notify_on_error=True
        )
        self.commands["pause"] = Command.raw_command(
            self.pause, delay_all=0, delay_user=0, level=500, notify_on_error=True
        )
        self.commands["resume"] = Command.raw_command(
            self.resume, delay_all=0, delay_user=0, level=500, notify_on_error=True
        )
        self.commands["volume"] = Command.raw_command(
            self.volume, delay_all=0, delay_user=0, level=500, notify_on_error=True
        )
        self.commands["showvideo"] = Command.raw_command(
            self.show_video, delay_all=0, delay_user=0, level=500, notify_on_error=True
        )
        self.commands["hidevideo"] = Command.raw_command(
            self.hide_video, delay_all=0, delay_user=0, level=500, notify_on_error=True
        )
        self.commands["voteskip"] = Command.raw_command(
            self.vote_skip, delay_all=0, delay_user=0, level=100, notify_on_error=True
        )
        self.commands["blacklist"] = Command.raw_command(
            self.blacklist, delay_all=0, delay_user=0, level=500, notify_on_error=True
        )
        self.commands["when"] = Command.raw_command(
            self.when, delay_all=0, delay_user=0, level=100, notify_on_error=True
        )
        self.commands["wrongsong"] = Command.raw_command(
            self.wrong_song, delay_all=0, delay_user=60, level=100, notify_on_error=True
        )
        if self.bot and self.bot.songrequest_manager.states["enabled"]:
            self.bot.songrequest_manager.load(self)

    def end_stream(self):
        self.bot.songrequest_manager.request_state_function(False)
        self.bot.songrequest_manager.auto_play_state_function(False)

    def enable(self, bot):
        if not self.bot:
            return

        self.bot.songrequest_manager.state("enabled", True)
        self.bot.songrequest_manager.load(self)
        HandlerManager.add_handler("on_stream_stop", self.end_stream)

    def disable(self, bot):
        if not self.bot:
            return

        self.bot.songrequest_manager.disable()
        HandlerManager.remove_handler("on_stream_stop", self.end_stream)

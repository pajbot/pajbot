from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable, Optional

import datetime
import logging

from pajbot import utils
from pajbot.apiwrappers.queup import QueUpAPI, QueUpQueueSong
from pajbot.managers.handler import HandlerManager
from pajbot.managers.redis import RedisManager
from pajbot.managers.schedule import ScheduleManager
from pajbot.models.command import Command, CommandExample
from pajbot.models.user import User
from pajbot.modules import BaseModule, ModuleSetting

if TYPE_CHECKING:
    from pajbot.bot import Bot

log = logging.getLogger(__name__)


class QueUpSongInfo:
    """Holds only the info relevant for displaying the song in chat."""

    def __init__(self, song_id: str, song_name: str, song_link: str, requester_name: str) -> None:
        self.song_id = song_id
        self.song_name = song_name
        self.song_link = song_link
        self.requester_name = requester_name


class QueUpModule(BaseModule):
    ID = __name__.split(".")[-1]
    NAME = "QueUp"
    DESCRIPTION = "Gets currently playing song from QueUp"
    CATEGORY = "Feature"
    SETTINGS = [
        ModuleSetting(
            key="room_name",
            label="QueUp room name. No spaces. Use the string after /join/ in the URL",
            type="text",
            required=True,
            placeholder="QueUp room name (i.e. pajlada)",
            default="pajlada",
            constraints={"min_str_len": 1, "max_str_len": 70},
        ),
        ModuleSetting(
            key="phrase_room_link",
            label="Room link message | Available arguments: {room_name}",
            type="text",
            required=True,
            placeholder="Request your songs at https://queup.net/join/{room_name}",
            default="Request your songs at https://queup.net/join/{room_name}",
            constraints={"min_str_len": 1, "max_str_len": 400},
        ),
        ModuleSetting(
            key="phrase_current_song",
            label="Current song message | Available arguments: {song_name}, {song_link}, {requester_name}",
            type="text",
            required=True,
            placeholder="Current song: {song_name}, link: {song_link} requested by {requester_name}",
            default="Current song: {song_name}, link: {song_link} requested by {requester_name}",
            constraints={"min_str_len": 1, "max_str_len": 400},
        ),
        ModuleSetting(
            key="phrase_no_current_song",
            label="Current song message when there's nothing playing",
            type="text",
            required=True,
            placeholder="There's no song playing right now BibleThump",
            default="There's no song playing right now BibleThump",
            constraints={"min_str_len": 1, "max_str_len": 400},
        ),
        ModuleSetting(
            key="phrase_previous_song",
            label="Previous song message | Available arguments: {song_name}, {song_link}, {requester_name}",
            type="text",
            required=True,
            placeholder="Previous song: {song_name}, link: {song_link} requested by {requester_name}",
            default="Previous song: {song_name}, link: {song_link} requested by {requester_name}",
            constraints={"min_str_len": 1, "max_str_len": 400},
        ),
        ModuleSetting(
            key="phrase_no_previous_song",
            label="Previous song message when there's nothing playing",
            type="text",
            required=True,
            placeholder="There's no previous song BibleThump",
            default="There's no previous song BibleThump",
            constraints={"min_str_len": 1, "max_str_len": 400},
        ),
        ModuleSetting(
            key="new_song_auto_enable",
            label="Automatically post a message in chat when a new song starts playing",
            type="boolean",
            required=True,
            default=False,
        ),
        ModuleSetting(
            key="new_song_online_chat_only",
            label="Enable automatic new song message in online chat only",
            type="boolean",
            required=True,
            default=True,
        ),
        ModuleSetting(
            key="phrase_new_song",
            label="New song message | Available arguments: {song_name}, {song_link}, {requester_name}",
            type="text",
            required=True,
            placeholder="Now playing: {song_name}, link: {song_link} requested by {requester_name}",
            default="Now playing: {song_name}, link: {song_link} requested by {requester_name}",
            constraints={"min_str_len": 1, "max_str_len": 400},
        ),
        ModuleSetting(
            key="global_cd",
            label="Global cooldown (seconds)",
            type="number",
            required=True,
            placeholder="",
            default=5,
            constraints={"min_value": 0, "max_value": 120},
        ),
        ModuleSetting(
            key="user_cd",
            label="Per-user cooldown (seconds)",
            type="number",
            required=True,
            placeholder="",
            default=15,
            constraints={"min_value": 0, "max_value": 240},
        ),
        ModuleSetting(key="if_qu_alias", label="Alias !qu to !queup", type="boolean", required=True, default=True),
        ModuleSetting(
            key="if_short_alias",
            label="Alias !queup [s, l, u] to !queup [song, link, update]",
            type="boolean",
            required=True,
            default=True,
        ),
        ModuleSetting(
            key="if_song_alias", label="Alias !song to !queup song", type="boolean", required=True, default=True
        ),
        ModuleSetting(
            key="if_lastsong_alias",
            label="Alias !lastsong to !queup previous",
            type="boolean",
            required=True,
            default=True,
        ),
        ModuleSetting(
            key="if_previoussong_alias",
            label="Alias !previoussong to !queup previous",
            type="boolean",
            required=True,
            default=True,
        ),
    ]

    def __init__(self, bot: Optional[Bot]) -> None:
        super().__init__(bot)
        self.api = QueUpAPI(RedisManager.get())
        self.scheduled_job = None

        # allows us to differentiate between "no song -> a song starts playing" vs "module was unintialized
        # (current song is also None) -> first fetch succeeds (which is not a condition where the new song
        # message should be triggered)
        self.is_first_automatic_fetch: bool = True
        self.last_seen_song_id: Optional[str] = None

    def cmd_link(self, bot: Bot, source: User, message: str, event: Any, **rest: Any) -> None:
        bot.send_message_to_user(
            source,
            self.settings["phrase_room_link"].format(room_name=self.settings["room_name"]),
            event,
            method="reply",
        )

    def cmd_song(self, bot: Bot, source: User, message: str, event: Any, **rest: Any) -> None:
        def on_success(song_info: Optional[QueUpSongInfo]) -> None:
            if song_info:
                response = self.get_phrase(
                    "phrase_current_song",
                    song_name=song_info.song_name,
                    song_link=song_info.song_link,
                    requester_name=song_info.requester_name,
                )
            else:
                response = self.get_phrase("phrase_no_current_song")

            bot.send_message_to_user(source, response, event, method="reply")

        def on_error(e: Exception) -> None:
            log.exception("QueUp API fetch for current song failed", exc_info=e)
            bot.send_message_to_user(
                source, "There was an error fetching the current QueUp song :/", event, method="reply"
            )

        self.api_request_and_callback(self.get_current_song, on_success, on_error)

    def cmd_previous_song(self, bot: Bot, source: User, message: str, event: Any, **rest: Any) -> None:
        def on_success(song_info: Optional[QueUpSongInfo]) -> None:
            if song_info:
                response = self.get_phrase(
                    "phrase_previous_song",
                    song_name=song_info.song_name,
                    song_link=song_info.song_link,
                    requester_name=song_info.requester_name,
                )
            else:
                response = self.get_phrase("phrase_no_previous_song")

            bot.send_message_to_user(source, response, event, method="reply")

        def on_error(e: Exception) -> None:
            log.exception("QueUp API fetch for previous song failed", exc_info=e)
            bot.send_message_to_user(
                source, "There was an error fetching the previous QueUp song :/", event, method="reply"
            )

        self.api_request_and_callback(self.get_previous_song, on_success, on_error)

    def on_scheduled_new_song_check(self) -> None:
        def on_success(song_info: Optional[QueUpSongInfo]) -> None:
            assert self.bot is not None

            new_song_id: Optional[str] = None

            if song_info:
                new_song_id = song_info.song_id

            # first fetch? then the "old song ID" is the new song ID
            if self.is_first_automatic_fetch:
                old_song_id = new_song_id
                self.is_first_automatic_fetch = False
            else:
                old_song_id = self.last_seen_song_id

            # remember the new song ID for the next scheduler invocation
            self.last_seen_song_id = new_song_id

            if new_song_id is None:
                # new song is None, i.e. end of queue
                return

            assert song_info is not None

            if old_song_id == new_song_id:
                # song is not new
                return

            # got a new song under song_info
            auto_msg = self.get_phrase(
                "phrase_new_song",
                song_name=song_info.song_name,
                song_link=song_info.song_link,
                requester_name=song_info.requester_name,
            )

            self.bot.say(auto_msg)

        def on_error(e: Exception) -> None:
            log.exception("Automatic QueUp song polling failed", exc_info=e)

        self.api_request_and_callback(self.get_current_song, on_success, on_error)

    def api_request_and_callback(
        self,
        api_fn: Callable[[], Optional[QueUpSongInfo]],
        on_success: Callable[[Optional[QueUpSongInfo]], None],
        on_error: Callable[[Exception], None],
    ) -> None:
        if self.bot is None:
            log.warning("QueUpModule.api_request_and_callback failed because bot is None")
            return

        def action_queue_action() -> None:
            assert self.bot is not None

            try:
                result = api_fn()
                self.bot.execute_now(on_success, result)
            except Exception as e:
                self.bot.execute_now(on_error, e)

        self.bot.action_queue.submit(action_queue_action)

    def process_queue_song_to_song_info(self, queue_song: Optional[QueUpQueueSong]) -> Optional[QueUpSongInfo]:
        """Processes a QueUpQueueSong instance (from the API) into a QueUpSongInfo object (for output to chat)"""

        # no current or past song -> no song info
        if queue_song is None:
            return None

        # Ensure the song is fit for use
        self.api.hydrate_song(queue_song)

        # Not sure how to skip this asseration, but hydrate_song will always ensure song_name and requester_name are set
        assert queue_song.song_name is not None
        assert queue_song.requester_name is not None

        song_id: str = queue_song.song_id
        song_name: str = queue_song.song_name
        song_link: str = self.api.get_song_link(song_id)
        requester_name: str = queue_song.requester_name

        return QueUpSongInfo(song_id=song_id, song_name=song_name, song_link=song_link, requester_name=requester_name)

    def get_current_song(self) -> Optional[QueUpSongInfo]:
        room_id = self.api.get_room_id(self.settings["room_name"])
        queue_song = self.api.get_current_song(room_id)

        # consider past songs (this happens if queup is currently switching the playing song)
        if queue_song is None:
            past_songs = self.api.get_past_songs(room_id)
            if len(past_songs) > 0:
                queue_song = past_songs[0]

            if queue_song is not None:
                self.api.hydrate_song(queue_song)
                # it was possible to fetch the last song from the history
                # check using queue_song.length and queue_song.played_at whether
                # this song has ended playing recently
                ended_playing = queue_song.played_at + queue_song.length
                time_since_song_end = utils.now() - ended_playing

                if time_since_song_end > datetime.timedelta(minutes=1):
                    # the song we fetched from the room history ended playing more than 1 minute ago
                    # so it is by no means the "current song" anymore.
                    queue_song = None

        return self.process_queue_song_to_song_info(queue_song)

    def get_previous_song(self) -> Optional[QueUpSongInfo]:
        room_id = self.api.get_room_id(self.settings["room_name"])

        past_songs = self.api.get_past_songs(room_id)

        queue_song: Optional[QueUpQueueSong] = None

        if len(past_songs) > 0:
            queue_song = past_songs[0]

        return self.process_queue_song_to_song_info(queue_song)

    def load_commands(self, **options) -> None:
        commands = {
            "link": Command.raw_command(
                self.cmd_link,
                level=100,
                delay_all=self.settings["global_cd"],
                delay_user=self.settings["user_cd"],
                description="Get link to your queup",
                examples=[
                    CommandExample(
                        None,
                        "Ask bot for queup link",
                        chat="user:!queup link\n" "bot:Request your songs at https://queup.net/join/pajlada",
                    ).parse()
                ],
            ),
            "song": Command.raw_command(
                self.cmd_song,
                level=100,
                delay_all=self.settings["global_cd"],
                delay_user=self.settings["user_cd"],
                description="Get current song",
                examples=[
                    CommandExample(
                        None,
                        "Ask bot for current song (YouTube)",
                        chat="user:!queup song\n"
                        "bot:Current song: NOMA - Brain Power, link: https://youtu.be/9R8aSKwTEMg requested by FabPotato69",
                    ).parse(),
                    CommandExample(
                        None,
                        "Ask bot for current song (SoundCloud)",
                        chat="user:!queup song\n"
                        "bot:Current song: This is Bondage, link: https://soundcloud.com/razq35/nightlife requested by karylul",
                    ).parse(),
                    CommandExample(
                        None,
                        "Ask bot for current song (nothing playing)",
                        chat="user:!queup song\n" "bot:There's no song playing right now BibleThump",
                    ).parse(),
                ],
            ),
            "previous": Command.raw_command(
                self.cmd_previous_song,
                level=100,
                delay_all=self.settings["global_cd"],
                delay_user=self.settings["user_cd"],
                description="Get previous song",
                examples=[
                    CommandExample(
                        None,
                        "Ask bot for current song (YouTube)",
                        chat="user:!queup song\n"
                        "bot:Current song: NOMA - Brain Power, link: https://youtu.be/9R8aSKwTEMg requested by FabPotato69",
                    ).parse(),
                    CommandExample(
                        None,
                        "Ask bot for current song (SoundCloud)",
                        chat="user:!queup song\n"
                        "bot:Current song: This is Bondage, link: https://soundcloud.com/razq35/nightlife requested by karylul",
                    ).parse(),
                    CommandExample(
                        None,
                        "Ask bot for current song (nothing playing)",
                        chat="user:!queup song\n" "bot:There's no song playing right now BibleThump",
                    ).parse(),
                ],
            ),
        }

        # alias :p
        commands["lastsong"] = commands["previous"]

        if self.settings["if_short_alias"]:
            commands["l"] = commands["link"]
            commands["s"] = commands["song"]

        self.commands["queup"] = Command.multiaction_command(
            level=100,
            default="link",  # If the user does not input any argument
            fallback="link",  # If the user inputs an invalid argument
            command="queup",
            commands=commands,
        )

        if self.settings["if_qu_alias"]:
            self.commands["qu"] = self.commands["queup"]

        if self.settings["if_song_alias"]:
            self.commands["song"] = commands["song"]

        if self.settings["if_previoussong_alias"]:
            self.commands["previoussong"] = commands["previous"]

        if self.settings["if_lastsong_alias"]:
            self.commands["lastsong"] = commands["previous"]

    def enable_job(self) -> None:
        if self.scheduled_job is not None:
            log.debug("queup: starting to poll for new songs")
            self.scheduled_job.resume()

    def disable_job(self) -> None:
        if self.scheduled_job is not None:
            log.debug("queup: will no longer poll for new songs")
            self.scheduled_job.pause()

        self.is_first_automatic_fetch = True
        self.last_seen_song_id = None

    def on_stream_start(self) -> bool:
        self.enable_job()
        return True

    def on_stream_stop(self) -> bool:
        if self.settings["new_song_online_chat_only"]:
            self.disable_job()
        return True

    def enable(self, bot: Optional[Bot]) -> None:
        if not bot:
            return

        HandlerManager.add_handler("on_stream_start", self.on_stream_start)
        HandlerManager.add_handler("on_stream_stop", self.on_stream_stop)

        if self.settings["new_song_auto_enable"]:
            self.scheduled_job = ScheduleManager.execute_every(15, self.on_scheduled_new_song_check)

            if bot.is_online:
                self.on_stream_start()
            else:
                self.on_stream_stop()

    def disable(self, bot: Optional[Bot]) -> None:
        if not bot:
            return

        HandlerManager.remove_handler("on_stream_start", self.on_stream_start)
        HandlerManager.remove_handler("on_stream_stop", self.on_stream_stop)

        self.disable_job()

        if self.scheduled_job is not None:
            self.scheduled_job.remove()
            self.scheduled_job = None

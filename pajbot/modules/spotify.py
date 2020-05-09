import logging

from pajbot.models.command import Command
from pajbot.modules import BaseModule
from pajbot.modules import ModuleSetting

log = logging.getLogger(__name__)


class SpotifyModule(BaseModule):

    ID = __name__.split(".")[-1]
    NAME = "Spotify"
    DESCRIPTION = "Gets song info from spotify"
    CATEGORY = "Feature"
    SETTINGS = [
        ModuleSetting(
            key="online_global_cd",
            label="Global cooldown (seconds)",
            type="number",
            required=True,
            placeholder="",
            default=5,
            constraints={"min_value": 0, "max_value": 120},
        ),
        ModuleSetting(
            key="online_user_cd",
            label="Per-user cooldown (seconds)",
            type="number",
            required=True,
            placeholder="",
            default=15,
            constraints={"min_value": 0, "max_value": 240},
        ),
        ModuleSetting(
            key="playing_streamlabs_media_message_layout",
            label="Message shown when !song is called from chat if a song is playing via mediashare and the user doesnt exist | Available arguments: {username}, {song_title}, {requestor}",
            type="text",
            required=True,
            placeholder="",
            default="@{username}, The current song is {song_title} requested by {requestor}",
        ),
        ModuleSetting(
            key="playing_spotify",
            label="Message shown when !song is called from chat if a song is playing in spotify | Available arguments: {username}, {song_title}, {artists}",
            type="text",
            required=True,
            placeholder="",
            default='@{username}, The current song is "{song_title}" by {artists}',
        ),
        ModuleSetting(
            key="no_song_playing",
            label="Message shown when !song is called from chat if there is no song playing | Available arguments: {username}",
            type="text",
            required=True,
            placeholder="",
            default="@{username}, There are no songs currently playing",
        ),
        ModuleSetting(
            key="show_song_when_stream_offline",
            label="Show a message of the currently playing song when the stream is offline",
            type="boolean",
            required=True,
            placeholder="",
            default=False,
        ),
        ModuleSetting(
            key="offline_song_message",
            label="Message shown when !song is called when the stream is offline. Requires above option to be enabled. | Available arguments: {username}",
            type="text",
            required=False,
            placeholder="",
            default="@{username}, Spotify songs are not shown when offline",
        ),
    ]

    def load_commands(self, **options):
        self.commands["song"] = Command.raw_command(
            self.current_song,
            delay_all=self.settings["online_global_cd"],
            delay_user=self.settings["online_user_cd"],
            description="Displayes the current song",
        )

    def current_song(self, bot, source, message, **rest):
        if not self.settings["show_song_when_stream_offline"] and (
            bot.stream_manager.current_stream is None or bot.stream_manager.current_stream.id is None
        ):
            if self.settings["offline_song_message"]:
                self.bot.say(self.settings["offline_song_message"].format(username=source))
            return False

        isPlaying, name, artists = self.bot.spotify_api.state(self.bot.spotify_token_manager)
        if not isPlaying:
            self.bot.say(self.settings["no_song_playing"].format(username=source))
            return False

        self.bot.say(
            self.settings["playing_spotify"].format(
                username=source, song_title=name, artists=", ".join([str(artist) for artist in artists])
            )
        )
        return True

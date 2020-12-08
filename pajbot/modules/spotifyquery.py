import logging

from pajbot.models.command import Command
from pajbot.modules import BaseModule
from pajbot.modules import ModuleSetting

log = logging.getLogger(__name__)


class SpotifySongQuery(BaseModule):

    ID = __name__.split(".")[-1]
    NAME = "SpotifySongQuery"
    DESCRIPTION = "Gets song info from spotify"
    CATEGORY = "Feature"
    SETTINGS = [
        ModuleSetting(
            key="online_global_cd",
            label="Global cooldown (seconds)",
            type="number",
            required=True,
            placeholder="",
            default=0,
            constraints={"min_value": 0, "max_value": 120},
        ),
        ModuleSetting(
            key="online_user_cd",
            label="Per-user cooldown (seconds)",
            type="number",
            required=True,
            placeholder="",
            default=5,
            constraints={"min_value": 0, "max_value": 240},
        ),
        ModuleSetting(
            key="playing_streamlabs_media_message_layout",
            label="Messaged showen when !song is called from chat if a song is playing via mediashare and the user doesnt exist",
            type="text",
            required=True,
            placeholder="",
            default="@{username}, the current song is {song_title} requested by @{requestor}",
        ),
        ModuleSetting(
            key="playing_spotify",
            label="Messaged showen when !song is called from chat if a song is playing in spotify",
            type="text",
            required=True,
            placeholder="",
            default='@{username}, the current song is "{song_title}" by {artists}',
        ),
        ModuleSetting(
            key="no_song_playing",
            label="Messaged showen when !song is called from chat if there is no song playing",
            type="text",
            required=True,
            placeholder="",
            default="@{username}, there are no songs currently playing",
        ),
        ModuleSetting(
            key="stream_offline",
            label="Messaged showen when !song is called from chat and the stream is offline",
            type="text",
            required=True,
            placeholder="",
            default="@{username}, the stream is currently offline",
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
        isPlaying, name, artists = self.bot.spotify_player_api.state(self.bot.spotify_token_manager)
        if not isPlaying:
            bot.say(self.settings["no_song_playing"].format(username=source.username_raw))
            return False
        bot.say(
            self.settings["playing_spotify"].format(
                username=source.username_raw, song_title=name, artists=", ".join([str(artist) for artist in artists])
            )
        )
        return True

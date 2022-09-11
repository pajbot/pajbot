import logging

from pajbot.models.command import Command, CommandExample
from pajbot.modules import BaseModule, ModuleSetting
from pajbot.streamhelper import StreamHelper

log = logging.getLogger(__name__)


class LastfmModule(BaseModule):
    ID = __name__.split(".")[-1]
    NAME = "LastFM module"
    DESCRIPTION = "This uses the LastFM api to fetch the current artist and songname that the streamer is listening to on spotify or youtube."
    CATEGORY = "Feature"
    SETTINGS = [
        ModuleSetting(
            key="api_key",
            label="LastFM Api Key",
            type="text",
            required=True,
            placeholder="i.e. abcedfg1235hfhafafajhf",
            default="",
        ),
        ModuleSetting(
            key="username",
            label="LastFM Username",
            type="text",
            required=True,
            placeholder="i.e. anniefuchsia",
            default="",
        ),
        ModuleSetting(
            key="no_song",
            label="Message to send when no song is playing | Available arguments: {streamer}",
            type="text",
            required=True,
            placeholder="{streamer} isn't playing any music right now... FeelsBadMan",
            default="{streamer} isn't playing any music right now... FeelsBadMan",
        ),
        ModuleSetting(
            key="current_song",
            label="Message to send when a song is playing | Available arguments: {streamer}, {song}",
            type="text",
            required=True,
            placeholder="Current song is 🎵 🎶 {song} 🎶 🎵",
            default="Current song is 🎵 🎶 {song} 🎶 🎵",
        ),
        ModuleSetting(
            key="cannot_fetch_song",
            label="Message to send when unable to fetch the song",
            type="text",
            required=True,
            placeholder="I'm having trouble fetching the song name... Please try again FeelsBadMan",
            default="I'm having trouble fetching the song name... Please try again FeelsBadMan",
        ),
        ModuleSetting(
            key="global_cd",
            label="Global cooldown (seconds)",
            type="number",
            required=True,
            placeholder="",
            default=30,
            constraints={"min_value": 0, "max_value": 120},
        ),
        ModuleSetting(
            key="user_cd",
            label="Per-user cooldown (seconds)",
            type="number",
            required=True,
            placeholder="",
            default=60,
            constraints={"min_value": 0, "max_value": 240},
        ),
        ModuleSetting(
            key="online_only",
            label="Only allow the LastFM commands to be run while the stream is online",
            type="boolean",
            required=True,
            default=True,
        ),
    ]

    def load_commands(self, **options):
        # TODO: Aliases should be set in settings?
        #       This way, it can be run alongside other modules
        self.commands["song"] = Command.raw_command(
            self.song,
            delay_all=self.settings["global_cd"],
            delay_user=self.settings["user_cd"],
            description="Check what that is playing on the stream",
            examples=[
                CommandExample(
                    None,
                    "Check the current song",
                    chat="user:!song\n"
                    f"bot: @pajlada {self.settings['current_song'].format(streamer=StreamHelper.get_streamer(), song='Adele - Hello')}",
                    description="Bot mentions the name of the song and the artist currently playing on stream",
                ).parse()
            ],
        )
        self.commands["currentsong"] = self.commands["song"]
        self.commands["nowplaying"] = self.commands["song"]
        self.commands["playing"] = self.commands["song"]

    def song(self, source, event, **rest) -> bool:
        if self.bot is None:
            log.warning("LastfmModule.song failed because bot is None")
            return False

        if self.settings["online_only"] and not self.bot.is_online:
            return False

        try:
            import pylast
        except ImportError:
            log.error("Missing required library for the LastFM Module: pylast")
            return False

        API_KEY = self.settings["api_key"]
        lastfmname = self.settings["username"]

        if len(API_KEY) < 10 or len(lastfmname) < 2:
            log.warning("You need to set up the Last FM API stuff in the Module settings.")
            return False

        try:

            network = pylast.LastFMNetwork(api_key=API_KEY, api_secret="", username=lastfmname, password_hash="")
            user = network.get_user(lastfmname)
            currentTrack = user.get_now_playing()
            payload = {"streamer": self.bot.streamer_display, "song": currentTrack, "source": "{source}"}

            if currentTrack is None:
                self.bot.send_message_to_user(source, self.get_phrase("no_song", **payload), event, method="reply")
            else:
                self.bot.send_message_to_user(source, self.get_phrase("current_song", **payload), event, method="reply")
        except pylast.WSError:
            log.error("LastFm username not found")
        except IndexError:
            self.bot.send_message_to_user(source, self.get_phrase("cannot_fetch_song"), event, method="reply")

        return True

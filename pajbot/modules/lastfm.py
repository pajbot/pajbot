import logging

from pajbot.models.command import Command
from pajbot.models.command import CommandExample
from pajbot.modules import BaseModule
from pajbot.modules import ModuleSetting

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
    ]

    def load_commands(self, **options):
        # TODO: Aliases should be set in settings?
        #       This way, it can be run alongside other modules
        self.commands["song"] = Command.raw_command(
            self.song,
            delay_all=12,
            delay_user=25,
            description="Check what that is playing on the stream",
            examples=[
                CommandExample(
                    None,
                    "Check the current song",
                    chat="user:!song\n" "bot: Current Song is \u2669\u266a\u266b Adele - Hello \u266c\u266b\u2669",
                    description="Bot mentions the name of the song and the artist currently playing on stream",
                ).parse()
            ],
        )
        self.commands["currentsong"] = self.commands["song"]
        self.commands["nowplaying"] = self.commands["song"]
        self.commands["playing"] = self.commands["song"]

    def song(self, bot, **rest):
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

            if currentTrack is None:
                bot.me(f"{bot.streamer} isn't playing music right now.. FeelsBadMan")
            else:
                bot.me(f"Current Song is \u2669\u266a\u266b {currentTrack} \u266c\u266b\u2669")
        except pylast.WSError:
            log.error("LastFm username not found")
        except IndexError:
            bot.me("I have trouble fetching the song name.. Please try again FeelsBadMan")

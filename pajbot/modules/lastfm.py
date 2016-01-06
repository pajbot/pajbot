import logging
import pylast

from pajbot.modules import BaseModule, ModuleSetting
from pajbot.models.command import Command

log = logging.getLogger(__name__)

class LastfmModule(BaseModule):
    ID = __name__.split('.')[-1]
    NAME = 'LastFM module'
    DESCRIPTION = 'This uses the LastFM api to fetch the current artist and songname that the streamer is listening to on spotify or youtube.'

    def load_commands(self, **options):
        self.commands['song'] = Command.raw_command(self.song,
                delay_all=12,
                delay_user=25,
                description='Check what that is playing on the stream',
                examples=[
                    CommandExample(None, 'Check the current song',
                        chat='user:!song\n'
                        'bot: Current Song is \u2669\u266a\u266b Adele - Hello \u266c\u266b\u2669',
                        description='Bot mentions the name of the song and the artist currently playing on stream').parse(),
                    ],
                )
        self.commands['currentsong'] = self.commands['song']
        self.commands['nowplaying'] = self.commands['song']
        self.commands['playing'] = self.commands['song']

    def song(self, **options):
        source = options['source']
        bot = options['bot']

        API_KEY = bot.config['lastfm']['api_key'] #"f6a3b7b12549aa211a6deec453c79417"
        lastfmname = bot.config['lastfm']['user'] #"anniefuchsia"
        network = pylast.LastFMNetwork(api_key = API_KEY, api_secret ="", username = lastfmname, password_hash ="")
        try:
            user = network.get_user(lastfmname)
            currentTrack = user.get_now_playing()
            if currentTrack == None:
                bot.me('{} isn\'t playing music right now!'.format(bot.streamer))
            else:
                bot.me('Current Song is \u2669\u266a\u266b {0} \u266c\u266b\u2669'.format(currentTrack))
        except IndexError:
            bot.me('I have trouble fetching the song name.. Please try again FeelsBadMan')

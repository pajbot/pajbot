import json
import logging
import re

import requests

from pajbot.models.command import Command
from pajbot.modules import BaseModule

log = logging.getLogger(__name__)


class DubtrackModule(BaseModule):
    AUTHOR = 'TalVivian @ github.com/TalVivian'
    ID = __name__.split('.')[-1]
    NAME = 'Dubtrack module'
    DESCRIPTION = 'Gets currently playing song from dubtrack'
    CATEGORY = 'Feature'
    SETTINGS = []

    def __init__(self, **options):
        super().__init__()
        self.room_name = ''
        self.song_name = ''
        self.song_id = ''
        self.song_link = ''

    def enable(self, bot):
        self.room_name = bot.config['dubtrack'].get('room_name')

    def get_room_link(self):
        return 'https://dubtrack.com/join/' + self.room_name

    def link(self, **options):
        bot = options['bot']
        bot.say(self.get_room_link())

    def clear(self):
        self.song_name = ''
        self.song_id = ''
        self.song_link = ''

    def update_song(self, force=False):
        if force:
            self.clear()

        url = 'https://api.dubtrack.fm/room/' + self.room_name

        r = requests.get(url)
        if r.status_code != 200:
            return

        text = json.loads(r.text)
        if text['code'] != 200:
            return

        data = text['data']['currentSong']
        if data is None:
            self.clear()
            return

        if self.song_id == data['songid']:
            return

        self.song_name = data['name']
        self.song_id = data['songid']

        if data['type'] == 'youtube':
            self.song_link = 'https://youtu.be/' + data['fkid']
        elif data['type'] == 'soundcloud':
            url = 'https://api.dubtrack.fm/song/' + data['songid'] + '/redirect'

            r = requests.get(url, allow_redirects=False)
            if r.status_code != 301:
                self.song_link = ''
                return

            new_song_link = r.headers['Location']
            self.song_link = re.sub('^http', 'https', new_song_link)
        else:
            self.song_link = ''

    def say_song(self, bot):
        if self.song_name == '':
            bot.say('There\'s no song playing right now FeelsBadMan')
            return

        if self.song_link == '':
            bot.say('Current song: {0}'.format(self.song_name))
            return

        bot.say('Current song: {0}, link: {1}'.format(self.song_name, self.song_link))

    def say_room(self, **options):
        bot = options['bot']
        bot.say('Current room: {0}'.format(self.room_name))

    def song(self, **options):
        self.update_song()
        self.say_song(options['bot'])

    def update(self, **options):
        self.update_song(force=True)
        self.say_song(options['bot'])

    def change_room(self, **options):
        bot = options['bot']
        message = options['message']
        if message is None:
            return

        self.clear()

        message_split = message.split()
        new_room_name = message_split[0]
        self.room_name = str(new_room_name)

        bot.say('Changed dubtrack room to: {0}, new link: {1}'.format(self.room_name, self.get_room_link()))

        self.song(bot=options['bot'])

    def load_commands(self, **options):
        commands = {
                'link': Command.raw_command(
                    self.link,
                    level=100,
                    delay_all=5,
                    delay_user=15,
                    description='Get link to your dubtrack',
                ),
                'song': Command.raw_command(
                    self.song,
                    level=100,
                    delay_all=5,
                    delay_user=15,
                    description='Get current song',
                    ),
                'update': Command.raw_command(
                    self.update,
                    level=500,
                    delay_all=0,
                    delay_user=0,
                    description='Force reloading the song and get current song',
                    ),
                'room': Command.raw_command(
                    self.say_room,
                    level=500,
                    delay_all=0,
                    delay_user=0,
                    description='Get dubtrack room',
                    ),
                'changeroom': Command.raw_command(
                    self.change_room,
                    level=500,
                    delay_all=0,
                    delay_user=0,
                    description='Change dubtrack room',
                    ),
                }
        commands['l'] = commands['link']
        commands['s'] = commands['song']
        commands['r'] = commands['room']
        commands['u'] = commands['update']
        commands['c'] = commands['changeroom']
        commands['ch'] = commands['changeroom']
        commands['chr'] = commands['changeroom']

        self.commands['dubtrack'] = Command.multiaction_command(
            level=100,
            default=commands['link'],
            command='dubtrack',
            commands=commands,
            )
        self.commands['dt'] = self.commands['dubtrack']

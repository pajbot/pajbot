import json
import logging
import re

import requests

from pajbot.models.command import Command
from pajbot.modules import BaseModule
from pajbot.modules import ModuleSetting

log = logging.getLogger(__name__)


class DubtrackModule(BaseModule):
    AUTHOR = 'TalVivian @ github.com/TalVivian'
    ID = __name__.split('.')[-1]
    NAME = 'Dubtrack module'
    DESCRIPTION = 'Gets currently playing song from dubtrack'
    CATEGORY = 'Feature'
    SETTINGS = [
            ModuleSetting(
                key='room_name',
                label='Dubtrack room',
                type='text',
                required=True,
                placeholder='Dubtrack room (i.e. pajlada)',
                default='pajlada',
                constraints={
                    'min_str_len': 2,
                    'max_str_len': 70,
                    }),
            ModuleSetting(
                key='phrase_current_song',
                label='Current song message if no link is available | Available arguments: {song_name}, {song_link}',
                type='text',
                required=True,
                placeholder='Current song: {song_name}, link: {song_link}',
                default='Current song: {song_name}, link: {song_link}',
                constraints={
                    'min_str_len': 10,
                    'max_str_len': 400,
                }),
            ModuleSetting(
                key='phrase_current_song_no_link',
                label='Current song message if no link is available | Available arguments: {song_name}',
                type='text',
                required=True,
                placeholder='Current song: {song_name}',
                default='Current song: {song_name}',
                constraints={
                    'min_str_len': 10,
                    'max_str_len': 400,
                }),
            ModuleSetting(
                key='phrase_room_link',
                label='Room link message | Available arguments: {room_name}',
                type='text',
                required=True,
                placeholder='Request your songs at https://dubtrack.fm/join/{room_name}',
                default='Request your songs at https://dubtrack.fm/join/{room_name}',
                constraints={
                    'min_str_len': 10,
                    'max_str_len': 400,
                }),
            ModuleSetting(
                key='room_link',
                label='Room link | Available arguments: {room_link}',
                type='text',
                required=True,
                placeholder='{user} won {bet} points in roulette and now has {points} points! FeelsGoodMan',
                default='{user} won {bet} points in roulette and now has {points} points! FeelsGoodMan',
                constraints={
                    'min_str_len': 10,
                    'max_str_len': 400,
                }),
                ]

    def __init__(self, **options):
        super().__init__()
        self.clear()

    def link(self, **options):
        bot = options['bot']
        arguments = {
                'room_name': self.settings['room_name']
                }
        bot.say(self.get_phrase('phrase_room_link', **arguments))

    def clear(self):
        self.song_name = None
        self.song_id = None
        self.song_link = None

    def update_song(self, force=False):
        if force:
            self.clear()

        url = 'https://api.dubtrack.fm/room/' + self.settings['room_name']

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
                self.song_link = None
                return

            new_song_link = r.headers['Location']
            self.song_link = re.sub('^http', 'https', new_song_link)
        else:
            self.song_link = None

    def say_song(self, bot):
        if self.song_name is None:
            bot.say('There\'s no song playing right now FeelsBadMan')
            return

        arguments = {
                'song_name': self.song_name
                }

        if self.song_link:
            arguments['song_link'] = self.song_link
            bot.say(self.get_phrase('phrase_current_song', **arguments))
        else:
            bot.say(self.get_phrase('phrase_current_song_no_link', **arguments))

    def song(self, **options):
        self.update_song()
        self.say_song(options['bot'])

    def update(self, **options):
        self.update_song(force=True)
        self.say_song(options['bot'])

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
                    run_in_thread=True,
                    ),
                'update': Command.raw_command(
                    self.update,
                    level=500,
                    delay_all=0,
                    delay_user=0,
                    description='Force reloading the song and get current song',
                    ),
                }
        commands['l'] = commands['link']
        commands['s'] = commands['song']
        commands['u'] = commands['update']

        self.commands['dubtrack'] = Command.multiaction_command(
            level=100,
            default='link',  # If the user does not input any argument
            fallback='link',  # If the user inputs an invalid argument
            command='dubtrack',
            commands=commands,
            )
        self.commands['dt'] = self.commands['dubtrack']
        self.commands['song'] = commands['song']

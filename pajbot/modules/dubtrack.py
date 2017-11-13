import html
import json
import logging
import re

import requests

import pajbot.models
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
                    'min_str_len': 1,
                    'max_str_len': 70,
                    }),
            ModuleSetting(
                key='phrase_room_link',
                label='Room link message | Available arguments: {room_name}',
                type='text',
                required=True,
                placeholder='Request your songs at https://dubtrack.fm/join/{room_name}',
                default='Request your songs at https://dubtrack.fm/join/{room_name}',
                constraints={
                    'min_str_len': 1,
                    'max_str_len': 400,
                }),
            ModuleSetting(
                key='phrase_current_song',
                label='Current song message | Available arguments: {song_name}, {song_link}',
                type='text',
                required=True,
                placeholder='Current song: {song_name}, link: {song_link}',
                default='Current song: {song_name}, link: {song_link}',
                constraints={
                    'min_str_len': 1,
                    'max_str_len': 400,
                }),
            ModuleSetting(
                key='phrase_current_song_no_link',
                label='Current song message if no song link is available | Available arguments: {song_name}',
                type='text',
                required=True,
                placeholder='Current song: {song_name}',
                default='Current song: {song_name}',
                constraints={
                    'min_str_len': 1,
                    'max_str_len': 400,
                }),
            ModuleSetting(
                key='phrase_no_current_song',
                label='Current song message when there\'s nothing playing',
                type='text',
                required=True,
                placeholder='There\'s no song playing right now FeelsBadMan',
                default='There\'s no song playing right now FeelsBadMan',
                constraints={
                    'min_str_len': 1,
                    'max_str_len': 400,
                }),
            ModuleSetting(
                key='global_cd',
                label='Global cooldown (seconds)',
                type='number',
                required=True,
                placeholder='',
                default=5,
                constraints={
                    'min_value': 0,
                    'max_value': 120,
                    }),
            ModuleSetting(
                key='user_cd',
                label='Per-user cooldown (seconds)',
                type='number',
                required=True,
                placeholder='',
                default=15,
                constraints={
                    'min_value': 0,
                    'max_value': 240,
                    }),
            ModuleSetting(
                key='if_dt_alias',
                label='Allow !dt as !dubtrack',
                type='boolean',
                required=True,
                default=True,
                    ),
            ModuleSetting(
                key='if_short_alias',
                label='Allow !dubtrack [s, l, u] as !dubtrack [song, link, update]',
                type='boolean',
                required=True,
                default=True,
                    ),
            ModuleSetting(
                key='if_song_alias',
                label='Allow !song as !dubtrack song',
                type='boolean',
                required=True,
                default=True,
                    ),
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
            log.warning('Dubtrack api not responding')
            self.clear()
            return

        text = json.loads(r.text)
        if text['code'] != 200:
            log.warning('Dubtrack api invalid response')
            self.clear()
            return

        data = text['data']['currentSong']
        if data is None:
            # No song playing
            self.clear()
            return

        if self.song_id == data['songid']:
            # No need to update song
            return

        raw_song_name = data['name']
        self.song_name = html.unescape(raw_song_name)
        self.song_id = data['songid']

        if data['type'] == 'youtube':
            self.song_link = 'https://youtu.be/' + data['fkid']
        elif data['type'] == 'soundcloud':
            url = 'https://api.dubtrack.fm/song/' + data['songid'] + '/redirect'

            self.song_link = None

            r = requests.get(url, allow_redirects=False)
            if r.status_code != 301:
                log.warning('Couldn\'t resolve soundcloud link')
                return

            new_song_link = r.headers['Location']
            self.song_link = re.sub('^http:', 'https:', new_song_link)
        else:
            log.warning('Unknown link type')
            self.song_link = None

    def say_song(self, bot):
        if self.song_name is None:
            bot.say(self.get_phrase('phrase_no_current_song'))
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
                'link': pajbot.models.command.Command.raw_command(
                    self.link,
                    level=100,
                    delay_all=self.settings['global_cd'],
                    delay_user=self.settings['user_cd'],
                    description='Get link to your dubtrack',
                    examples=[
                        pajbot.models.command.CommandExample(
                            None,
                            'Ask bot for dubtrack link',
                            chat='user:!dubtrack link\n'
                            'bot:Request your songs at https://dubtrack.fm/join/pajlada').parse(),
                        ],
                    ),
                'song': pajbot.models.command.Command.raw_command(
                    self.song,
                    level=100,
                    delay_all=self.settings['global_cd'],
                    delay_user=self.settings['user_cd'],
                    description='Get current song',
                    run_in_thread=True,
                    examples=[
                        pajbot.models.command.CommandExample(
                            None,
                            'Ask bot for current song (youtube)',
                            chat='user:!dubtrack song\n'
                            'bot:Current song: NOMA - Brain Power, link: https://youtu.be/9R8aSKwTEMg').parse(),
                        pajbot.models.command.CommandExample(
                            None,
                            'Ask bot for current song (soundcloud)',
                            chat='user:!dubtrack song\n'
                            'bot:Current song: This is Bondage, link: https://soundcloud.com/razq35/nightlife').parse(),
                        pajbot.models.command.CommandExample(
                            None,
                            'Ask bot for current song (nothing playing)',
                            chat='user:!dubtrack song\n'
                            'bot:There\'s no song playing right now FeelsBadMan').parse(),
                        ],
                    ),
                'update': pajbot.models.command.Command.raw_command(
                    self.update,
                    level=500,
                    delay_all=self.settings['global_cd'],
                    delay_user=self.settings['user_cd'],
                    description='Force reloading the song and get current song',
                    run_in_thread=True,
                    ),
                }
        if self.settings['if_short_alias']:
            commands['l'] = commands['link']
            commands['s'] = commands['song']
            commands['u'] = commands['update']

        self.commands['dubtrack'] = pajbot.models.command.Command.multiaction_command(
            level=100,
            default='link',  # If the user does not input any argument
            fallback='link',  # If the user inputs an invalid argument
            command='dubtrack',
            commands=commands,
            )

        if self.settings['if_dt_alias']:
            self.commands['dt'] = self.commands['dubtrack']

        if self.settings['if_song_alias']:
            self.commands['song'] = commands['song']

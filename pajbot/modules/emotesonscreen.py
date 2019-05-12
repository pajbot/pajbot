import logging
import random

from pajbot.managers.handler import HandlerManager
from pajbot.modules import BaseModule
from pajbot.modules import ModuleSetting

log = logging.getLogger(__name__)


class EmotesOnScreenModule(BaseModule):

    ID = __name__.split('.')[-1]
    NAME = 'Emotes on Screen (CLR)'
    DESCRIPTION = 'Shows one or more emotes on screen per message'
    CATEGORY = 'Feature'
    SETTINGS = [
            ModuleSetting(
                key='emote_whitelist',
                label='Whitelisted emotes (separate by spaces). Leave empty to use the blacklist.',
                type='text',
                required=True,
                placeholder='i.e. Kappa Keepo PogChamp KKona',
                default=''),
            ModuleSetting(
                key='emote_blacklist',
                label='Blacklisted emotes (separate by spaces). Leave empty to allow all emotes.',
                type='text',
                required=True,
                placeholder='i.e. Kappa Keepo PogChamp KKona',
                default=''),
            ModuleSetting(
                key='emote_opacity',
                label='Emote opacity (in percent)',
                type='number',
                required=True,
                placeholder='',
                default=100,
                constraints={
                    'min_value': 0,
                    'max_value': 100,
            }),
            ModuleSetting(
                key='max_emotes_per_message',
                label='Maximum number of emotes per message that may appear on the screen. Set to 500 for unlimited.',
                type='number',
                required=True,
                placeholder='',
                default=1,
                constraints={
                    'min_value': 0,
                    'max_value': 500,
            }),
            ModuleSetting(
                key='emote_persistence_time',
                label='Time in milliseconds until emotes disappear on screen',
                type='number',
                required=True,
                placeholder='',
                default=5000,
                constraints={
                    'min_value': 500,
                    'max_value': 60000,
            }),
            ModuleSetting(
                key='emote_onscreen_scale',
                label='Scale emotes onscreen by this factor (100 = normal size)',
                type='number',
                required=True,
                placeholder='',
                default=100,
                constraints={
                    'min_value': 0,
                    'max_value': 100000,
            }),
                ]

    def is_emote_allowed(self, emoteCode):
        if len(self.settings['emote_whitelist'].strip()) > 0:
            return emoteCode in self.settings['emote_whitelist']

        return emoteCode not in self.settings['emote_blacklist']

    def on_message(self, source, message, emotes, whisper, urls, event):
        if whisper:
            return

        emote_instances = []
        for emote in emotes:
           if not self.is_emote_allowed(emote['code']):
               continue

           for i in range(emote['count']):
               emote_instances.append(emote)

        sample_size = min(len(emote_instances), self.settings['max_emotes_per_message'])
        sent_emote_instances = random.sample(emote_instances, sample_size)

        if len(sent_emote_instances) < 1:
            return

        # keep a mapping emote code -> emote
        # so we can count emote occurrance by emote code
        # and then later map back to the emote
        emote_code_to_emote = dict()
        for emote in emotes:
            emote_code_to_emote[emote['code']] = emote

        # map emote code -> shown count
        # can't use the emote itself as the key
        sent_emotes_map = dict()
        for emote in sent_emote_instances:
            sent_emotes_map[emote['code']] = sent_emotes_map.get(emote['code'], 0) + 1

        # turn the map into a list
        sent_emotes = []
        for emote_code, shown_count in sent_emotes_map.items():
            sent_emotes.append({'emote': emote_code_to_emote[emote_code], 'shown_count': shown_count})

        self.bot.websocket_manager.emit('new_emotes', {
            'emotes': sent_emotes,
            'opacity': self.settings['emote_opacity'],
            'persistence_time': self.settings['emote_persistence_time'],
            'scale': self.settings['emote_onscreen_scale']
        })

    def enable(self, bot):
        self.bot = bot
        HandlerManager.add_handler('on_message', self.on_message)

    def disable(self, bot):
        HandlerManager.remove_handler('on_message', self.on_message)

import logging

from pajbot.managers.handler import HandlerManager
from pajbot.modules import BaseModule

log = logging.getLogger(__name__)


class EmoteComboModule(BaseModule):

    ID = __name__.split('.')[-1]
    NAME = 'Emote Combo (web interface)'
    DESCRIPTION = 'Shows emote combos in the web interface CLR thing'
    CATEGORY = 'Feature'
    SETTINGS = [
                ]

    def __init__(self):
        super().__init__()
        self.bot = None

        self.emote_count = 0
        self.current_emote = None

    def inc_emote_count(self):
        self.emote_count += 1
        if self.emote_count >= 5:
            self.bot.websocket_manager.emit('emote_combo', {'emote': self.current_emote, 'count': self.emote_count})

    def reset(self):
        self.emote_count = 0
        self.current_emote = None

    def on_message(self, source, message, emotes, whisper, urls, event):
        if whisper is False:
            if len(emotes) == 0:
                # Ignore messages without any emotes
                return True

            prev_code = None
            # Check if the message contains more than one unique emotes
            for emote in emotes:
                if prev_code is not None:
                    if prev_code != emote['code']:
                        # The message contained more than 1 unique emote, reset.
                        self.reset()
                        return True
                else:
                    prev_code = emote['code']

            emote = emotes[0]

            # forsenGASM and gachiGASM are the same emotes, so they should count for the same combo
            if emote['code'] == 'forsenGASM':
                emote['code'] = 'gachiGASM'

            if self.current_emote is not None:
                if not self.current_emote['code'] == emote['code']:
                    # The emote of this message is not the one we were previously counting, reset.
                    # We do not stop.
                    # We start counting this emote instead.
                    self.reset()

            if self.current_emote is None:
                self.current_emote = {
                        'code': emote['code'],
                        'twitch_id': emote.get('twitch_id', None),
                        'bttv_hash': emote.get('bttv_hash', None),
                        'ffz_id': emote.get('ffz_id', None),
                        }

            self.inc_emote_count()

    def enable(self, bot):
        HandlerManager.add_handler('on_message', self.on_message)
        self.bot = bot

    def disable(self, bot):
        HandlerManager.remove_handler('on_message', self.on_message)

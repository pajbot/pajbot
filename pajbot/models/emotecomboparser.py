import re
import logging

log = logging.getLogger('pajbot')


class EmoteComboParser:
    def __init__(self, bot):
        self.bot = bot
        self.emote_count = 0
        self.current_emote = None

    def inc_emote_count(self):
        self.emote_count += 1
        if self.emote_count >= 5:
            self.bot.websocket_manager.emit('emote_combo', {'emote': self.current_emote, 'count': self.emote_count})

    def reset(self):
        self.emote_count = 0
        self.current_emote = None

    def parse_line(self, msg, source, emotes):
        if len(emotes) == 0:
            # Ignore messages without any emotes
            return False

        prev_code = None
        for emote in emotes:
            if prev_code is not None:
                if prev_code != emote['code']:
                    # The message contained more than 1 unique emote, reset.
                    self.reset()
                    return False
            else:
                prev_code = emote['code']

        emote = emotes[0]
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
                    'bttv_hash': emote.get('bttv_hash', None)
                    }

        self.inc_emote_count()

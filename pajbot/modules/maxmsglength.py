import logging

from pajbot.modules import BaseModule, ModuleSetting
from pajbot.models.command import Command

log = logging.getLogger(__name__)

class MaxMsgLengthModule(BaseModule):

    ID = __name__.split('.')[-1]
    NAME = 'Maximum message length'
    DESCRIPTION = 'Times out users who post messages that contain too many characters.'
    SETTINGS = [
            ModuleSetting(
                key='max_msg_length',
                label='Max message length',
                type='number',
                required=True,
                placeholder='',
                default=400,
                constraints={
                    'min_value': 40,
                    'max_value': 1000,
                    }),
            ModuleSetting(
                key='timeout_length',
                label='Timeout length',
                type='number',
                required=True,
                placeholder='Timeout length in seconds',
                default=120,
                constraints={
                    'min_value': 30,
                    'max_value': 3600,
                    })
                ]

    def __init__(self):
        super().__init__()
        self.bot = None

    def on_pubmsg(self, source, message):
        if len(message) > self.settings['max_msg_length'] and source.level < 500 and source.moderator is False:
            duration, punishment = self.bot.timeout_warn(source, self.settings['timeout_length'])
            if duration > 0:
                self.bot.whisper(source.username, 'You have been {punishment} because your message was too long.'.format(punishment=punishment))
            return False

    def enable(self, bot):
        if bot:
            bot.add_handler('on_pubmsg', self.on_pubmsg)
            self.bot = bot

    def disable(self, bot):
        if bot:
            bot.remove_handler('on_pubmsg', self.on_pubmsg)

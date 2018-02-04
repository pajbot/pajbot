import logging

from pajbot.managers.handler import HandlerManager
from pajbot.modules import BaseModule
from pajbot.modules import ModuleSetting

log = logging.getLogger(__name__)


class CaseCheckerModule(BaseModule):
    ID = __name__.split('.')[-1]
    NAME = 'Case checker'
    DESCRIPTION = 'Times out users who post messages that contain too many characters.'
    CATEGORY = 'Filter'
    SETTINGS = [
            ModuleSetting(
                key='timeout_uppercase',
                label='Timeout any uppercase in messages',
                type='boolean',
                required=True,
                default=False),
            ModuleSetting(
                key='timeout_lowercase',
                label='Timeout any lowercase in messages',
                type='boolean',
                required=True,
                default=False),
            ModuleSetting(
                key='bypass_level',
                label='Level to bypass module',
                type='number',
                required=True,
                placeholder='',
                default=500,
                constraints={
                    'min_value': 100,
                    'max_value': 1000,
                    })
                ]

    def __init__(self):
        super().__init__()
        self.bot = None

    def on_pubmsg(self, source, message):
        if source.level > self.settings['bypass_level'] or source.moderator is True:
            return True

        if self.bot.is_online:
            if self.settings['timeout_uppercase'] and any(c.isupper() for c in message):
                self.bot.timeout_user(source, 3, reason='no uppercase characters allowed')
                return False

            if self.settings['timeout_lowercase'] and any(c.islower() for c in message):
                self.bot.timeout_user(source, 3, reason='NO LOWERCASE CHARACTERS ALLOWED')
                return False

        return True

    def enable(self, bot):
        HandlerManager.add_handler('on_pubmsg', self.on_pubmsg)
        self.bot = bot

    def disable(self, bot):
        HandlerManager.remove_handler('on_pubmsg', self.on_pubmsg)

import logging
import re
import datetime
import math

from pajbot.modules import BaseModule, ModuleSetting
from pajbot.models.command import Command
from pajbot.models.handler import HandlerManager

log = logging.getLogger(__name__)

class PaidTimeoutModule(BaseModule):

    ID = __name__.split('.')[-1]
    NAME = 'Paid Timeout'
    DESCRIPTION = 'Allows user to time out other users with points'
    CATEGORY = 'Feature'
    SETTINGS = [
            ModuleSetting(
                key='command_name',
                label='Command name (i.e. $timeout)',
                type='text',
                required=True,
                placeholder='Command name (no !)',
                default='timeout',
                constraints={
                    'min_str_len': 2,
                    'max_str_len': 15,
                    }),
            ModuleSetting(
                key='timeout_length',
                label='Timeout length',
                type='number',
                required=True,
                placeholder='Timeout length in seconds',
                default=60,
                constraints={
                    'min_value': 1,
                    'max_value': 3600,
                    }),
            ModuleSetting(
                key='cost',
                label='Point cost',
                type='number',
                required=True,
                placeholder='Point cost',
                default=400,
                constraints={
                    'min_value': 1,
                    'max_value': 10000,
                    }),
            ]

    def paid_timeout(self, **options):
        message = options['message']
        bot = options['bot']
        source = options['source']

        _time = self.settings['timeout_length']
        _cost = self.settings['cost']

        if message is None or len(message) == 0:
            return False

        username = message.split(' ')[0]
        if len(username) < 2:
            return False

        victim = bot.users.find(username)
        if victim is None:
            bot.whisper(source.username, 'This user does not exist FailFish')
            return False

        """
        if victim == source:
            bot.whisper(source.username, 'You can\'t timeout yourself FailFish')
            return False
            """

        if victim.level >= 500:
            bot.whisper(source.username, 'This person has mod privileges, timeouting this person is not worth it.')
            return False

        now = datetime.datetime.now()
        if victim.timed_out is True and victim.timeout_end > now:
            victim.timeout_end += datetime.timedelta(seconds=_time)
            bot.whisper(victim.username, '{victim.username}, you were timed out for an additional {time} seconds by {source.username}'.format(
                victim=victim,
                source=source,
                time=_time))
            bot.whisper(source.username, 'You just used {0} points to time out {1} for an additional {2} seconds.'.format(_cost, username, _time))
            num_seconds = int((victim.timeout_end - now).total_seconds())
            bot._timeout(username, num_seconds)
        else:
            bot.whisper(source.username, 'You just used {0} points to time out {1} for {2} seconds.'.format(_cost, username, _time))
            bot.whisper(username, '{0} just timed you out for {1} seconds. /w {2} !$unbanme to unban yourself for points forsenMoney'.format(source.username, _time, bot.nickname))
            bot._timeout(username, _time)
            victim.timed_out = True
            victim.timeout_start = now
            victim.timeout_end = now + datetime.timedelta(seconds=_time)

        payload = {'user': source.username, 'victim': victim.username}
        bot.websocket_manager.emit('timeout', payload)
        HandlerManager.trigger('on_paid_timeout',
                source, victim, _cost,
                stop_on_false=False)

    def load_commands(self, **options):
        self.commands[self.settings['command_name'].lower().replace('!', '').replace(' ', '')] = Command.raw_command(self.paid_timeout, cost=self.settings['cost'])

class PaidTimeoutDiscountModule(BaseModule):

    ID = 'paidtimeoutdiscount'
    NAME = 'Paid Timeout Discount'
    DESCRIPTION = 'Allows user to time out other users with points'
    CATEGORY = 'Feature'
    PARENT_MODULE = PaidTimeoutModule
    # No settings to add yet. would like to have the message customizeable
    # would also like to have the discounts customizeable
    SETTINGS = []

    def on_paid_timeout(self, source, victim, cost):
        log.info('PAID TIMEOUT OCCURED')
        # Discounts here!
        discounts = {
                'trump_sub': (0.5, 'Trump (50%)'),
                'massan_sub': (0.45, 'Massan (55%)'),
                'athene_sub': (0.45, 'Athene (55%)'),
                'nostam_sub': (0.4, 'Nostam (60%)'),
                'reynad_sub': (0.8, 'Reynad (20%)'),
                'forsen_sub': (0.95, 'Forsen (5%)'),
                }

        added_discount = 1.0
        whisper_msg = []
        for tag, data in discounts.items():
            discount, text = data
            if tag in victim.tags:
                whisper_msg.append(text)
                added_discount *= discount

        if len(whisper_msg) > 0:
            actual_discount = 1.0 - added_discount
            refund = math.trunc(cost * actual_discount)
            if refund > 0:
                source.points += refund
                self.bot.whisper(source.username, 'You have been refunded {refund} points courtesy of TheMysil, because the user you timed out matched the following discounts: {discount_str}'.format(refund=refund, discount_str=', '.join(whisper_msg)))

    def enable(self, bot):
        HandlerManager.add_handler('on_paid_timeout', self.on_paid_timeout)
        self.bot = bot

    def disable(self, bot):
        HandlerManager.remove_handler('on_paid_timeout', self.on_paid_timeout)

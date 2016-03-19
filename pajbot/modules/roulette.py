import datetime
import logging
import math

from numpy import random

from pajbot.models.command import Command
from pajbot.models.command import CommandExample
from pajbot.models.db import DBManager
from pajbot.models.handler import HandlerManager
from pajbot.models.roulette import Roulette
from pajbot.modules import BaseModule
from pajbot.modules import ModuleSetting

log = logging.getLogger(__name__)

class RouletteModule(BaseModule):

    ID = __name__.split('.')[-1]
    NAME = 'Roulette'
    DESCRIPTION = 'Lets players roulette with themselves for points'
    CATEGORY = 'Game'
    SETTINGS = [
            ModuleSetting(
                key='rigged_percentage',
                label='Rigged %, lower = more chance of winning. 50 = 50% of winning. 25 = 75% of winning',
                type='number',
                required=True,
                placeholder='',
                default=50,
                constraints={
                    'min_value': 1,
                    'max_value': 100,
                    }),
            ModuleSetting(
                key='online_global_cd',
                label='Global cooldown (seconds)',
                type='number',
                required=True,
                placeholder='',
                default=0,
                constraints={
                    'min_value': 0,
                    'max_value': 120,
                    }),
            ModuleSetting(
                key='online_user_cd',
                label='Per-user cooldown (seconds)',
                type='number',
                required=True,
                placeholder='',
                default=60,
                constraints={
                    'min_value': 0,
                    'max_value': 240,
                    }),
            ModuleSetting(
                key='min_roulette_amount',
                label='Minimum roulette amount',
                type='number',
                required=True,
                placeholder='',
                default=1,
                constraints={
                    'min_value': 1,
                    'max_value': 3000,
                    }),
            ModuleSetting(
                key='only_roulette_after_sub',
                label='Only allow roulettes after sub',
                type='boolean',
                required=True,
                default=False),
            ModuleSetting(
                key='after_sub_roulette_time',
                label='How long after a sub people can roulette (seconds)',
                type='number',
                required=True,
                placeholder='',
                default=30,
                constraints={
                    'min_value': 5,
                    'max_value': 3600,
                    }),
                ]

    def __init__(self):
        super().__init__()
        self.last_sub = None

    def load_commands(self, **options):
        self.commands['roulette'] = Command.raw_command(self.roulette,
                delay_all=self.settings['online_global_cd'],
                delay_user=self.settings['online_user_cd'],
                description='Roulette for points',
                examples=[
                    CommandExample(None, 'Roulette for 69 points',
                        chat='user:!roulette 69\n'
                        'bot:pajlada won 69 points in roulette! FeelsGoodMan',
                        description='Do a roulette for 69 points').parse(),
                    ],
                )

    def rigged_random_result(self):
        return random.randint(1, 100) > self.settings['rigged_percentage']

    def roulette(self, **options):
        if self.settings['only_roulette_after_sub']:
            if self.last_sub is None:
                return False
            if datetime.datetime.now() - self.last_sub > datetime.timedelta(seconds=self.settings['after_sub_roulette_time']):
                return False

        message = options['message']
        user = options['source']
        bot = options['bot']

        if message is None:
            bot.whisper(user.username, 'I didn\'t recognize your bet! Usage: !roulette 150 to bet 150 points')
            return False

        msg_split = message.split(' ')
        if msg_split[0].lower() in ('all', 'allin'):
            bet = user.points_available()
        elif msg_split[0].endswith('%'):
            try:
                percentage = int(msg_split[0][:-1])
                if percentage < 1 or percentage > 100:
                    bot.whisper(user.username, 'To bet with percentages you need to specify a number between 1 and 100 (like !roulette 50%)')
                    return False

                bet = math.floor(user.points_available() * (percentage / 100))
            except (ValueError, TypeError):
                bot.whisper(user.username, 'Invalid percentage specified haHAA')
                return False
        else:
            try:
                bet = int(message.split(' ')[0])
            except (ValueError, TypeError):
                bot.whisper(user.username, 'I didn\'t recognize your bet! Usage: !roulette 150 to bet 150 points')
                return False

        if not user.can_afford(bet):
            bot.whisper(user.username, 'You don\'t have enough points to do a roulette for {} points :('.format(bet))
            return False

        if bet < self.settings['min_roulette_amount']:
            bot.whisper(user.username, 'You have to bet at least {} point! :('.format(self.settings['min_roulette_amount']))
            return False

        # Calculating the result
        result = self.rigged_random_result()
        points = bet if result else -bet
        user.points += points

        with DBManager.create_session_scope() as db_session:
            r = Roulette(user.id, points)
            db_session.add(r)

        if points > 0:
            bot.me('{0} won {1} points in roulette and now has {2} points! FeelsGoodMan'.format(user.username_raw, bet, user.points_available()))
        else:
            bot.me('{0} lost {1} points in roulette and now has {2} points! FeelsBadMan'.format(user.username_raw, bet, user.points_available()))

        HandlerManager.trigger('on_roulette_finish', user, points)

    def on_user_sub(self, user):
        self.last_sub = datetime.datetime.now()
        if self.settings['only_roulette_after_sub']:
            self.bot.say('Rouletting is now allowed for {} seconds! PogChamp'.format(self.settings['after_sub_roulette_time']))

    def on_user_resub(self, user, num_months):
        self.last_sub = datetime.datetime.now()
        if self.settings['only_roulette_after_sub']:
            self.bot.say('Rouletting is now allowed for {} seconds! PogChamp'.format(self.settings['after_sub_roulette_time']))

    def enable(self, bot):
        self.bot = bot

        HandlerManager.add_handler('on_user_sub', self.on_user_sub)
        HandlerManager.add_handler('on_user_resub', self.on_user_resub)

    def disable(self, bot):
        HandlerManager.remove_handler('on_user_sub', self.on_user_sub)
        HandlerManager.remove_handler('on_user_resub', self.on_user_resub)

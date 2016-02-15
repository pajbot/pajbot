import logging
import datetime

from pajbot.modules import BaseModule, ModuleSetting
from pajbot.models.command import Command, CommandExample
from pajbot.models.handler import HandlerManager

from numpy import random

log = logging.getLogger(__name__)

class RouletteModule(BaseModule):

    ID = __name__.split('.')[-1]
    NAME = 'Roulette (mini game)'
    DESCRIPTION = 'Lets players roulette with themselves for points'
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
                ]

    def load_commands(self, **options):
        self.commands['roulette'] = Command.raw_command(self.roulette,
                delay_all=self.settings['online_global_cd'],
                delay_user=self.settings['online_user_cd'],
                description='Roulette for points',
                examples=[
                    CommandExample(None, 'Roulette for 69 points',
                        chat='user:!roulette 69\n'
                        'bot:You have challenged Karl_Kons for 0 points',
                        description='Duel Karl_Kons for 0 points').parse(),
                    ],
                )

    def rigged_random_result(user):
        rigged_subs = {
            'trump_sub': 80,
            'massan_sub': 99,
            'nostam_sub': 70,
            'reynad_sub': 75,
        }
        
        rigged_value = self.settings['rigged_percentage']
        
        for tag, data in rigged_subs.items():
            if tag in user.tags:
                if(rigged_value < data):
                    rigged_value = data
                
        return random.randint(1, 100) > rigged_value

    def roulette(self, **options):
        message = options['message']
        user = options['source']
        bot = options['bot']

        try:
            bet = int(message.split(' ')[0])
        except (ValueError, TypeError, AttributeError):
            bot.whisper(user.username, 'I didn\'t recognize your bet! Usage: !roulette 150 to bet 150 points')
            return False

        if bet > user.points:
            bot.whisper(user.username, 'You don\'t have enough points to do a roulette for {} points :('.format(bet))
            return False

        if bet < self.settings['min_roulette_amount']:
            bot.whisper(user.username, 'You have to bet at least {} point! :('.format(self.settings['min_roulette_amount']))
            return False

        # Calculating the result
        result = self.rigged_random_result(user)
        points = bet if result else -bet
        user.points += points

        if points > 0:
            bot.me('{0} won {1} points in roulette! FeelsGoodMan'.format(user.username_raw, bet))
        else:
            bot.me('{0} lost {1} points in roulette! FeelsBadMan'.format(user.username_raw, bet))

        HandlerManager.trigger('on_roulette_finish', user, points)

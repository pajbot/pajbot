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
                    })
                ]

    def load_commands(self, **options):
        self.commands['roulette'] = Command.raw_command(self.roulette,
                delay_all=0,
                delay_user=60,
                description='Roulette for points',
                examples=[
                    CommandExample(None, 'Roulette for 69 points',
                        chat='user:!roulette 69\n'
                        'bot:You have challenged Karl_Kons for 0 points',
                        description='Duel Karl_Kons for 0 points').parse(),
                    ],
                )

    def rigged_random_result(self):
        return random.randint(1, 100) > self.settings['rigged_percentage']

    def roulette(self, **options):
        message = options['message']
        user = options['source']
        bot = options['bot']

        try:
            bet = int(message)
        except (ValueError, TypeError):
            bot.me('Sorry, {0}, I didn\'t recognize your bet! FeelsBadMan'.format(user.username_raw))
            return False

        if bet > user.points:
            bot.me('Sorry, {0}, you don\'t have enough points! FeelsBadMan'.format(user.username_raw))
            return False

        if bet <= 0:
            bot.me('Sorry, {0}, you have to bet at least 1 point! FeelsBadMan'.format(user.username_raw))
            return False

        bot.me('{0}, your roulette for {1} points has begun! PogChamp'.format(user.username_raw, bet))

        # Calculating the result
        result = self.rigged_random_result()
        points = bet if result else -bet
        user.points += points

        if points > 0:
            bot.execute_delayed(
                    2, bot.me, ('{0} won {1} points in roulette! FeelsGoodMan'.format(user.username_raw, bet), )
            )
        else:
            bot.execute_delayed(
                    2, bot.me, ('{0} lost {1} points in roulette! FeelsBadMan'.format(user.username_raw, bet), )
            )

        HandlerManager.trigger('on_roulette_finish', user, points)

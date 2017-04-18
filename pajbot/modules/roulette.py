import datetime
import logging

from numpy import random

import pajbot.exc
import pajbot.models
import pajbot.utils
from pajbot.managers.db import DBManager
from pajbot.managers.handler import HandlerManager
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
                key='message_won',
                label='Won message | Available arguments: {bet}, {points}, {user}',
                type='text',
                required=True,
                placeholder='{user} won {bet} points in roulette and now has {points} points! FeelsGoodMan',
                default='{user} won {bet} points in roulette and now has {points} points! FeelsGoodMan',
                constraints={
                    'min_str_len': 10,
                    'max_str_len': 400,
                }),
            ModuleSetting(
                key='message_lost',
                label='Lost message | Available arguments: {bet}, {points}, {user}',
                type='text',
                required=True,
                placeholder='{user} lost {bet} points in roulette and now has {points} points! FeelsBadMan',
                default='{user} lost {bet} points in roulette and now has {points} points! FeelsBadMan',
                constraints={
                    'min_str_len': 10,
                    'max_str_len': 400,
                }),
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
                key='can_execute_with_whisper',
                label='Allow users to roulette in whispers',
                type='boolean',
                required=True,
                default=False),
            ModuleSetting(
                key='options_output',
                label='Result output options',
                type='options',
                required=True,
                default='1. Show results in chat',
                options=[
                    '1. Show results in chat',
                    '2. Show results in whispers',
                    '3. Show results in chat if it\'s over X points else it will be whispered.',
                    ]),
            ModuleSetting(
                key='min_show_points',
                label='Min points you need to win or lose (if options 3)',
                type='number',
                required=True,
                placeholder='',
                default=100,
                constraints={
                    'min_value': 1,
                    'max_value': 150000,
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
        self.commands['roulette'] = pajbot.models.command.Command.raw_command(self.roulette,
                delay_all=self.settings['online_global_cd'],
                delay_user=self.settings['online_user_cd'],
                description='Roulette for points',
                can_execute_with_whisper=self.settings['can_execute_with_whisper'],
                examples=[
                    pajbot.models.command.CommandExample(None, 'Roulette for 69 points',
                        chat='user:!roulette 69\n'
                        'bot:pajlada won 69 points in roulette! FeelsGoodMan',
                        description='Do a roulette for 69 points').parse(),
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
        try:
            bet = pajbot.utils.parse_points_amount(user, msg_split[0])
        except pajbot.exc.InvalidPointAmount as e:
            bot.whisper(user.username, str(e))
            return False

        if not user.can_afford(bet):
            bot.whisper(user.username, 'You don\'t have enough points to do a roulette for {} points :('.format(bet))
            return False

        if bet < self.settings['min_roulette_amount']:
            bot.whisper(user.username, 'You have to bet at least {} point! :('.format(self.settings['min_roulette_amount']))
            return False

        # Calculating the result
        result = self.rigged_random_result(user)
        points = bet if result else -bet
        user.points += points

        with DBManager.create_session_scope() as db_session:
            r = Roulette(user.id, points)
            db_session.add(r)

        arguments = {
            'bet': bet,
            'user': user.username_raw,
            'points': user.points_available()
        }

        if points > 0:
            out_message = self.get_phrase('message_won', **arguments)
        else:
            out_message = self.get_phrase('message_lost', **arguments)

        if self.settings['options_output'] == '1. Show results in chat':
            bot.me(out_message)
        if self.settings['options_output'] == '2. Show results in whispers':
            bot.whisper(user.username, out_message)
        if self.settings['options_output'] == '3. Show results in chat if it\'s over X points else it will be whispered.':
            if abs(points) >= self.settings['min_show_points']:
                bot.me(out_message)
            else:
                bot.whisper(user.username, out_message)

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

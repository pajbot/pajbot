import logging
import math

from numpy import random

import pajbot.models
from pajbot.managers.handler import HandlerManager
from pajbot.modules import BaseModule
from pajbot.modules import ModuleSetting
from pajbot.streamhelper import StreamHelper

log = logging.getLogger(__name__)


def generate_winner_list(winners):
    """ Takes a list of winners, and combines them into a string. """
    return ', '.join([winner.username_raw for winner in winners])


class RaffleModule(BaseModule):

    ID = __name__.split('.')[-1]
    NAME = 'Raffle'
    DESCRIPTION = 'Users can participate in a raffle to win points.'
    CATEGORY = 'Game'
    SETTINGS = [
            ModuleSetting(
                key='message_start',
                label='Start message | Available arguments: {length}, {points}',
                type='text',
                required=True,
                placeholder='.me A raffle has begun for {points} points. type !join to join the raffle! The raffle will end in {length} seconds',
                default='.me A raffle has begun for {points} points. type !join to join the raffle! The raffle will end in {length} seconds',
                constraints={
                    'min_str_len': 10,
                    'max_str_len': 400,
                }),
            ModuleSetting(
                key='message_running',
                label='Running message | Available arguments: {length}, {points}',
                type='text',
                required=True,
                placeholder='.me The raffle for {points} points ends in {length} seconds! Type !join to join the raffle!',
                default='.me The raffle for {points} points ends in {length} seconds! Type !join to join the raffle!',
                constraints={
                    'min_str_len': 10,
                    'max_str_len': 400,
                }),
            ModuleSetting(
                key='message_start_multi',
                label='Start message (multi) | Available arguments: {length}, {points}',
                type='text',
                required=True,
                placeholder='.me A multi-raffle has begun for {points} points. type !join to join the raffle! The raffle will end in {length} seconds',
                default='.me A multi-raffle has begun for {points} points. type !join to join the raffle! The raffle will end in {length} seconds',
                constraints={
                    'min_str_len': 10,
                    'max_str_len': 400,
                }),
            ModuleSetting(
                key='message_running_multi',
                label='Running message (multi) | Available arguments: {length}, {points}',
                type='text',
                required=True,
                placeholder='.me The multi-raffle for {points} points ends in {length} seconds! Type !join to join the raffle!',
                default='.me The multi-raffle for {points} points ends in {length} seconds! Type !join to join the raffle!',
                constraints={
                    'min_str_len': 10,
                    'max_str_len': 400,
                }),
            ModuleSetting(
                key='single_max_points',
                label='Max points for a single raffle',
                type='number',
                required=True,
                placeholder='',
                default=3000,
                constraints={
                    'min_value': 0,
                    'max_value': 35000,
                    }),
            ModuleSetting(
                key='max_length',
                label='Max length for a single raffle in seconds',
                type='number',
                required=True,
                placeholder='',
                default=120,
                constraints={
                    'min_value': 0,
                    'max_value': 1200,
                    }),
            ModuleSetting(
                key='allow_negative_raffles',
                label='Allow negative raffles',
                type='boolean',
                required=True,
                default=True),
            ModuleSetting(
                key='max_negative_points',
                label='Max negative points for a single raffle',
                type='number',
                required=True,
                placeholder='',
                default=3000,
                constraints={
                    'min_value': 1,
                    'max_value': 35000,
                    }),
            ModuleSetting(
                key='multi_enabled',
                label='Enable multi-raffles (!multiraffle/!mraffle)',
                type='boolean',
                required=True,
                default=True),
            ModuleSetting(
                key='multi_max_points',
                label='Max points for a multi raffle',
                type='number',
                required=True,
                placeholder='',
                default=100000,
                constraints={
                    'min_value': 0,
                    'max_value': 1000000,
                    }),
            ModuleSetting(
                key='multi_max_length',
                label='Max length for a multi raffle in seconds',
                type='number',
                required=True,
                placeholder='',
                default=600,
                constraints={
                    'min_value': 0,
                    'max_value': 1200,
                    }),
            ModuleSetting(
                key='multi_allow_negative_raffles',
                label='Allow negative multi raffles',
                type='boolean',
                required=True,
                default=True),
            ModuleSetting(
                key='multi_max_negative_points',
                label='Max negative points for a multi raffle',
                type='number',
                required=True,
                placeholder='',
                default=10000,
                constraints={
                    'min_value': 1,
                    'max_value': 100000,
                    }),
            ModuleSetting(
                key='multi_raffle_on_sub',
                label='Start a multi raffle when someone subscribes',
                type='boolean',
                required=True,
                default=False),
            ModuleSetting(
                key='default_raffle_type',
                label='Default raffle (What raffle type !raffle should invoke)',
                type='options',
                required=True,
                default='Single Raffle',
                options=[
                    'Single Raffle',
                    'Multi Raffle',
                    ]),
            ModuleSetting(
                key='show_on_clr',
                label='Show raffles on the clr overlay',
                type='boolean',
                required=True,
                default=True),
            ]

    def __init__(self):
        super().__init__()

        self.raffle_running = False
        self.raffle_users = []
        self.raffle_points = 0
        self.raffle_length = 0

    def load_commands(self, **options):
        self.commands['singleraffle'] = pajbot.models.command.Command.raw_command(self.raffle,
                delay_all=0,
                delay_user=0,
                level=500,
                description='Start a raffle for points',
                command='raffle',
                examples=[
                    pajbot.models.command.CommandExample(None, 'Start a raffle for 69 points',
                        chat='user:!raffle 69\n'
                        'bot:A raffle has begun for 69 points. Type !join to join the raffle! The raffle will end in 60 seconds.',
                        description='Start a 60-second raffle for 69 points').parse(),
                    pajbot.models.command.CommandExample(None, 'Start a raffle with a different length',
                        chat='user:!raffle 69 30\n'
                        'bot:A raffle has begun for 69 points. Type !join to join the raffle! The raffle will end in 30 seconds.',
                        description='Start a 30-second raffle for 69 points').parse(),
                    ],
                )
        self.commands['sraffle'] = self.commands['singleraffle']
        self.commands['join'] = pajbot.models.command.Command.raw_command(self.join,
                delay_all=0,
                delay_user=5,
                description='Join a running raffle',
                examples=[
                    pajbot.models.command.CommandExample(None, 'Join a running raffle',
                        chat='user:!join',
                        description='You don\'t get confirmation whether you joined the raffle or not.').parse(),
                    ],
                )
        if self.settings['multi_enabled']:
            self.commands['multiraffle'] = pajbot.models.command.Command.raw_command(self.multi_raffle,
                    delay_all=0,
                    delay_user=0,
                    level=500,
                    description='Start a multi-raffle for points',
                    command='multiraffle',
                    examples=[
                        pajbot.models.command.CommandExample(None, 'Start a multi-raffle for 69 points',
                            chat='user:!multiraffle 69\n'
                            'bot:A multi-raffle has begun for 69 points. Type !join to join the raffle! The raffle will end in 60 seconds.',
                            description='Start a 60-second raffle for 69 points').parse(),
                        pajbot.models.command.CommandExample(None, 'Start a multi-raffle with a different length',
                            chat='user:!multiraffle 69 30\n'
                            'bot:A multi-raffle has begun for 69 points. Type !join to join the raffle! The raffle will end in 30 seconds.',
                            description='Start a 30-second multi-raffle for 69 points').parse(),
                        ],
                    )
            self.commands['mraffle'] = self.commands['multiraffle']

        if self.settings['default_raffle_type'] == 'Multi Raffle' and self.settings['multi_enabled']:
            self.commands['raffle'] = self.commands['multiraffle']
        else:
            self.commands['raffle'] = self.commands['singleraffle']

    def raffle(self, **options):
        bot = options['bot']
        source = options['source']
        message = options['message']

        if self.raffle_running is True:
            bot.say('{0}, a raffle is already running OMGScoots'.format(source.username_raw))
            return False

        self.raffle_users = []
        self.raffle_running = True
        self.raffle_points = 100
        self.raffle_length = 60

        try:
            if message is not None and self.settings['allow_negative_raffles'] is True:
                self.raffle_points = int(message.split()[0])
            if message is not None and self.settings['allow_negative_raffles'] is False:
                if int(message.split()[0]) >= 0:
                    self.raffle_points = int(message.split()[0])
        except (IndexError, ValueError, TypeError):
            pass

        try:
            if message is not None:
                if int(message.split()[1]) >= 5:
                    self.raffle_length = int(message.split()[1])
        except (IndexError, ValueError, TypeError):
            pass

        if self.raffle_points >= 0:
            self.raffle_points = min(self.raffle_points, self.settings['single_max_points'])
        if self.raffle_points <= -1:
            self.raffle_points = max(self.raffle_points, -self.settings['max_negative_points'])

        self.raffle_length = min(self.raffle_length, self.settings['max_length'])

        if self.settings['show_on_clr']:
            bot.websocket_manager.emit('notification', {'message': 'A raffle has been started!'})
            bot.execute_delayed(0.75, bot.websocket_manager.emit, ('notification', {'message': 'Type !join to enter!'}))

        arguments = {'length': self.raffle_length, 'points': self.raffle_points}
        bot.say(self.get_phrase('message_start', **arguments))
        arguments = {'length': round(self.raffle_length * 0.75), 'points': self.raffle_points}
        bot.execute_delayed(self.raffle_length * 0.25, bot.say, (self.get_phrase('message_running', **arguments), ))
        arguments = {'length': round(self.raffle_length * 0.50), 'points': self.raffle_points}
        bot.execute_delayed(self.raffle_length * 0.50, bot.say, (self.get_phrase('message_running', **arguments), ))
        arguments = {'length': round(self.raffle_length * 0.25), 'points': self.raffle_points}
        bot.execute_delayed(self.raffle_length * 0.75, bot.say, (self.get_phrase('message_running', **arguments), ))

        bot.execute_delayed(self.raffle_length, self.end_raffle)

    def join(self, **options):
        source = options['source']
        if not self.raffle_running:
            return False

        for user in self.raffle_users:
            if user == source:
                return False

        # Added user to the raffle
        self.raffle_users.append(source)

    def end_raffle(self):
        if not self.raffle_running:
            return False

        self.raffle_running = False

        if len(self.raffle_users) == 0:
            self.bot.me('Wow, no one joined the raffle DansGame')
            return False

        winner = random.choice(self.raffle_users)

        self.raffle_users = []

        if self.settings['show_on_clr']:
            self.bot.websocket_manager.emit('notification', {'message': '{} won {} points in the raffle!'.format(winner.username_raw, self.raffle_points)})
            self.bot.me('The raffle has finished! {0} won {1} points! PogChamp'.format(winner.username_raw, self.raffle_points))

        winner.points += self.raffle_points

        winner.save()

        HandlerManager.trigger('on_raffle_win', winner, self.raffle_points)

    def multi_start_raffle(self, points, length):
        if self.raffle_running:
            return False

        self.raffle_users = []
        self.raffle_running = True
        self.raffle_points = points
        self.raffle_length = length

        if self.raffle_points >= 0:
            self.raffle_points = min(self.raffle_points, self.settings['multi_max_points'])
        if self.raffle_points <= -1:
            self.raffle_points = max(self.raffle_points, -self.settings['multi_max_negative_points'])

        self.raffle_length = min(self.raffle_length, self.settings['multi_max_length'])

        if self.settings['show_on_clr']:
            self.bot.websocket_manager.emit('notification', {'message': 'A raffle has been started!'})
            self.bot.execute_delayed(0.75, self.bot.websocket_manager.emit, ('notification', {'message': 'Type !join to enter!'}))

        arguments = {'length': self.raffle_length, 'points': self.raffle_points}
        self.bot.say(self.get_phrase('message_start_multi', **arguments))
        arguments = {'length': round(self.raffle_length * 0.75), 'points': self.raffle_points}
        self.bot.execute_delayed(self.raffle_length * 0.25, self.bot.say, (self.get_phrase('message_running_multi', **arguments), ))
        arguments = {'length': round(self.raffle_length * 0.50), 'points': self.raffle_points}
        self.bot.execute_delayed(self.raffle_length * 0.50, self.bot.say, (self.get_phrase('message_running_multi', **arguments), ))
        arguments = {'length': round(self.raffle_length * 0.25), 'points': self.raffle_points}
        self.bot.execute_delayed(self.raffle_length * 0.75, self.bot.say, (self.get_phrase('message_running_multi', **arguments), ))

        self.bot.execute_delayed(self.raffle_length, self.multi_end_raffle)

    def multi_raffle(self, **options):
        bot = options['bot']
        source = options['source']
        message = options['message']

        if self.raffle_running is True:
            bot.say('{0}, a raffle is already running OMGScoots'.format(source.username_raw))
            return False

        points = 100
        try:
            if message is not None and self.settings['multi_allow_negative_raffles'] is True:
                points = int(message.split()[0])
            if message is not None and self.settings['multi_allow_negative_raffles'] is False:
                if int(message.split()[0]) >= 0:
                    points = int(message.split()[0])
        except (IndexError, ValueError, TypeError):
            pass

        length = 60
        try:
            if message is not None:
                if int(message.split()[1]) >= 5:
                    length = int(message.split()[1])
        except (IndexError, ValueError, TypeError):
            pass

        self.multi_start_raffle(points, length)

    def multi_end_raffle(self):
        if not self.raffle_running:
            return False

        self.raffle_running = False

        if len(self.raffle_users) == 0:
            self.bot.me('Wow, no one joined the raffle DansGame')
            return False

        # Shuffle the list of participants
        random.shuffle(self.raffle_users)

        num_participants = len(self.raffle_users)

        abs_points = abs(self.raffle_points)

        max_winners = min(num_participants, 200)
        min_point_award = 100
        negative = self.raffle_points < 0

        # Decide how we should pick the winners
        log.info('Num participants: {}'.format(num_participants))
        for winner_percentage in [x * 0.01 for x in range(1, 26)]:
            log.info('Winner percentage: {}'.format(winner_percentage))
            num_winners = math.ceil(num_participants * winner_percentage)
            points_per_user = math.ceil(abs_points / num_winners)
            log.info('nw: {}, ppu: {}'.format(num_winners, points_per_user))

            if num_winners > max_winners:
                num_winners = max_winners
                points_per_user = math.ceil(abs_points / num_winners)
                break
            elif points_per_user < min_point_award:
                num_winners = max(1, min(math.floor(abs_points / min_point_award), num_participants))
                points_per_user = math.ceil(abs_points / num_winners)
                break

        log.info('k done. got {} winners'.format(num_winners))
        winners = self.raffle_users[:num_winners]
        self.raffle_users = []

        if negative:
            points_per_user *= -1

        self.bot.me('The multi-raffle has finished! {0} users won {1} points each! PogChamp'.format(len(winners), points_per_user))

        winners_arr = []
        for winner in winners:
            winner.points += points_per_user
            winners_arr.append(winner)

            winners_str = generate_winner_list(winners_arr)
            if len(winners_str) > 300:
                self.bot.me('{} won {} points each!'.format(winners_str, points_per_user))
                winners_arr = []

            winner.save()

        if len(winners_arr) > 0:
            winners_str = generate_winner_list(winners_arr)
            self.bot.me('{} won {} points each!'.format(winners_str, points_per_user))

        HandlerManager.trigger('on_multiraffle_win', winners, points_per_user)

    def on_user_sub(self, user):
        if self.settings['multi_raffle_on_sub'] is False:
            return

        MAX_REWARD = 10000

        points = StreamHelper.get_viewers() * 5
        if points == 0:
            points = 100
        length = 30

        points = min(points, MAX_REWARD)

        self.multi_start_raffle(points, length)

    def on_user_resub(self, user, num_months):
        if self.settings['multi_raffle_on_sub'] is False:
            return

        MAX_REWARD = 10000

        points = StreamHelper.get_viewers() * 5
        if points == 0:
            points = 100
        length = 30

        points = min(points, MAX_REWARD)

        points += (num_months - 1) * 500

        self.multi_start_raffle(points, length)

    def enable(self, bot):
        self.bot = bot

        HandlerManager.add_handler('on_user_sub', self.on_user_sub)
        HandlerManager.add_handler('on_user_resub', self.on_user_resub)

    def disable(self, bot):
        HandlerManager.remove_handler('on_user_sub', self.on_user_sub)
        HandlerManager.remove_handler('on_user_resub', self.on_user_resub)

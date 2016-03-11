import logging
import math

from numpy import random

from pajbot.models.command import Command
from pajbot.models.command import CommandExample
from pajbot.models.handler import HandlerManager
from pajbot.modules import BaseModule
from pajbot.modules import ModuleSetting
from pajbot.streamhelper import StreamHelper

log = logging.getLogger(__name__)


class RaffleModule(BaseModule):

    ID = __name__.split('.')[-1]
    NAME = 'Raffle'
    DESCRIPTION = 'Users can participate in a raffle to win points.'
    CATEGORY = 'Game'
    SETTINGS = [
            ModuleSetting(
                key='max_points',
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
            ]

    def __init__(self):
        super().__init__()

        self.raffle_running = False
        self.raffle_users = []
        self.raffle_points = 0
        self.raffle_length = 0

    def load_commands(self, **options):
        self.commands['raffle'] = Command.raw_command(self.raffle,
                delay_all=0,
                delay_user=0,
                level=500,
                description='Start a raffle for points',
                examples=[
                    CommandExample(None, 'Start a raffle for 69 points',
                        chat='user:!raffle 69\n'
                        'bot:A raffle has begun for 69 points. Type !join to join the raffle! The raffle will end in in 60 seconds.',
                        description='Start a 60-second raffle for 69 points').parse(),
                    CommandExample(None, 'Start a raffle with a different length',
                        chat='user:!raffle 69 30\n'
                        'bot:A raffle has begun for 69 points. Type !join to join the raffle! The raffle will end in in 30 seconds.',
                        description='Start a 30-second raffle for 69 points').parse(),
                    ],
                )
        self.commands['join'] = Command.raw_command(self.join,
                delay_all=0,
                delay_user=5,
                description='Join a running raffle',
                examples=[
                    CommandExample(None, 'Join a running raffle',
                        chat='user:!join',
                        description='You don\'t get confirmation whether you joined the raffle or not.').parse(),
                    ],
                )

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
            self.raffle_points = min(self.raffle_points, self.settings['max_points'])
        if self.raffle_points <= -1:
            self.raffle_points = max(self.raffle_points, -self.settings['max_negative_points'])

        self.raffle_length = min(self.raffle_length, self.settings['max_length'])

        bot.websocket_manager.emit('notification', {'message': 'A raffle has been started!'})
        bot.execute_delayed(0.75, bot.websocket_manager.emit, ('notification', {'message': 'Type !join to enter!'}))

        bot.me('A raffle has begun for {} points. type !join to join the raffle! The raffle will end in {} seconds'.format(self.raffle_points, self.raffle_length))
        bot.execute_delayed(self.raffle_length * 0.25, bot.me, ('The raffle for {} points ends in {} seconds! Type !join to join the raffle!'.format(self.raffle_points, round(self.raffle_length * 0.75)), ))
        bot.execute_delayed(self.raffle_length * 0.50, bot.me, ('The raffle for {} points ends in {} seconds! Type !join to join the raffle!'.format(self.raffle_points, round(self.raffle_length * 0.50)), ))
        bot.execute_delayed(self.raffle_length * 0.75, bot.me, ('The raffle for {} points ends in {} seconds! Type !join to join the raffle!'.format(self.raffle_points, round(self.raffle_length * 0.25)), ))

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

        self.bot.websocket_manager.emit('notification', {'message': '{} won {} points in the raffle!'.format(winner.username_raw, self.raffle_points)})
        self.bot.me('The raffle has finished! {0} won {1} points! PogChamp'.format(winner.username_raw, self.raffle_points))

        winner.points += self.raffle_points

        HandlerManager.trigger('on_raffle_win', winner, self.raffle_points)

    def enable(self, bot):
        self.bot = bot

class MultiRaffleModule(BaseModule):

    ID = 'multiraffle'
    NAME = 'Multi Raffle'
    DESCRIPTION = 'Split out points between multiple users'
    CATEGORY = 'Game'
    PARENT_MODULE = RaffleModule
    SETTINGS = [
            ModuleSetting(
                key='max_points',
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
                key='max_length',
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
                key='allow_negative_raffles',
                label='Allow negative multi raffles',
                type='boolean',
                required=True,
                default=True),
            ModuleSetting(
                key='max_negative_points',
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
                key='raffle_on_sub',
                label='Start a raffle when someone subscribes',
                type='boolean',
                required=True,
                default=False),
            ]

    def load_commands(self, **options):
        self.commands['multiraffle'] = Command.raw_command(self.raffle,
                delay_all=0,
                delay_user=0,
                level=500,
                description='Start a multi-raffle for points',
                examples=[
                    CommandExample(None, 'Start a multi-raffle for 69 points',
                        chat='user:!multiraffle 69\n'
                        'bot:A multi-raffle has begun for 69 points. Type !join to join the raffle! The raffle will end in in 60 seconds.',
                        description='Start a 60-second raffle for 69 points').parse(),
                    CommandExample(None, 'Start a multi-raffle with a different length',
                        chat='user:!multiraffle 69 30\n'
                        'bot:A multi-raffle has begun for 69 points. Type !join to join the raffle! The raffle will end in in 30 seconds.',
                        description='Start a 30-second multi-raffle for 69 points').parse(),
                    ],
                )

    def start_raffle(self, points, length):
        if self.parent_module.raffle_running:
            return False

        self.parent_module.raffle_users = []
        self.parent_module.raffle_running = True
        self.parent_module.raffle_points = points
        self.parent_module.raffle_length = length

        if self.parent_module.raffle_points >= 0:
            self.parent_module.raffle_points = min(self.parent_module.raffle_points, self.settings['max_points'])
        if self.parent_module.raffle_points <= -1:
            self.parent_module.raffle_points = max(self.parent_module.raffle_points, -self.settings['max_negative_points'])

        self.parent_module.raffle_length = min(self.parent_module.raffle_length, self.settings['max_length'])

        self.bot.websocket_manager.emit('notification', {'message': 'A raffle has been started!'})
        self.bot.execute_delayed(0.75, self.bot.websocket_manager.emit, ('notification', {'message': 'Type !join to enter!'}))

        self.bot.me('A multi-raffle has begun, {} points will be split among the winners. type !join to join the raffle! The raffle will end in {} seconds'.format(self.parent_module.raffle_points, self.parent_module.raffle_length))
        self.bot.execute_delayed(self.parent_module.raffle_length * 0.25, self.bot.me, ('The multi-raffle for {} points ends in {} seconds! Type !join to join the raffle!'.format(self.parent_module.raffle_points, round(self.parent_module.raffle_length * 0.75)), ))
        self.bot.execute_delayed(self.parent_module.raffle_length * 0.50, self.bot.me, ('The multi-raffle for {} points ends in {} seconds! Type !join to join the raffle!'.format(self.parent_module.raffle_points, round(self.parent_module.raffle_length * 0.50)), ))
        self.bot.execute_delayed(self.parent_module.raffle_length * 0.75, self.bot.me, ('The multi-raffle for {} points ends in {} seconds! Type !join to join the raffle!'.format(self.parent_module.raffle_points, round(self.parent_module.raffle_length * 0.25)), ))

        self.bot.execute_delayed(self.parent_module.raffle_length, self.end_raffle)

    def raffle(self, **options):
        bot = options['bot']
        source = options['source']
        message = options['message']

        if self.parent_module.raffle_running is True:
            bot.say('{0}, a raffle is already running OMGScoots'.format(source.username_raw))
            return False

        points = 100
        try:
            if message is not None and self.settings['allow_negative_raffles'] is True:
                points = int(message.split()[0])
            if message is not None and self.settings['allow_negative_raffles'] is False:
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

        self.start_raffle(points, length)

    def generate_winner_list(self, winners):
        """ Takes a list of winners, and combines them into a string. """
        return ', '.join([winner.username_raw for winner in winners])

    def end_raffle(self):
        if not self.parent_module.raffle_running:
            return False

        self.parent_module.raffle_running = False

        if len(self.parent_module.raffle_users) == 0:
            self.bot.me('Wow, no one joined the raffle DansGame')
            return False

        # Shuffle the list of participants
        random.shuffle(self.parent_module.raffle_users)

        num_participants = len(self.parent_module.raffle_users)

        abs_points = abs(self.parent_module.raffle_points)

        max_winners = min(num_participants, 200)
        min_point_award = 100
        negative = self.parent_module.raffle_points < 0

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
        winners = self.parent_module.raffle_users[:num_winners]
        self.parent_module.raffle_users = []

        if negative:
            points_per_user *= -1

        """
        self.bot.websocket_manager.emit('notification', {'message': '{} won {} points in the raffle!'.format(winner.username_raw, self.parent_module.raffle_points)})
        self.bot.me('The raffle has finished! {0} won {1} points! PogChamp'.format(winner.username_raw, self.parent_module.raffle_points))
        """
        self.bot.me('The multi-raffle has finished! {0} users won {1} points each! PogChamp'.format(len(winners), points_per_user))

        winners_arr = []
        for winner in winners:
            winner.points += points_per_user
            winners_arr.append(winner)

            winners_str = self.generate_winner_list(winners_arr)
            if len(winners_str) > 300:
                self.bot.me('{} won {} points each!'.format(winners_str, points_per_user))
                winners_arr = []

        if len(winners_arr) > 0:
            winners_str = self.generate_winner_list(winners_arr)
            self.bot.me('{} won {} points each!'.format(winners_str, points_per_user))

        HandlerManager.trigger('on_multiraffle_win', winners, points_per_user)

    def on_user_sub(self, user):
        if self.settings['raffle_on_sub'] is False:
            return

        MAX_REWARD = 10000

        points = StreamHelper.get_viewers() * 5
        if points == 0:
            points = 100
        length = 30

        points = min(points, MAX_REWARD)

        self.start_raffle(points, length)

    def on_user_resub(self, user, num_months):
        if self.settings['raffle_on_sub'] is False:
            return

        MAX_REWARD = 10000

        points = StreamHelper.get_viewers() * 5
        if points == 0:
            points = 100
        length = 30

        points = min(points, MAX_REWARD)

        points += (num_months - 1) * 500

        self.start_raffle(points, length)

    def enable(self, bot):
        self.bot = bot

        HandlerManager.add_handler('on_user_sub', self.on_user_sub)
        HandlerManager.add_handler('on_user_resub', self.on_user_resub)

    def disable(self, bot):
        HandlerManager.remove_handler('on_user_sub', self.on_user_sub)
        HandlerManager.remove_handler('on_user_resub', self.on_user_resub)

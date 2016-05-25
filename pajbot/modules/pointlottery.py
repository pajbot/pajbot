import logging

from numpy import random

import pajbot.models
from pajbot.modules.base import BaseModule

log = logging.getLogger(__name__)


class PointLotteryModule(BaseModule):
    ID = __name__.split('.')[-1]
    NAME = 'Point Lottery'
    DESCRIPTION = 'Lets players participate in lottery for points'
    CATEGORY = 'Game'
    SETTINGS = []

    def __init__(self):
        super().__init__()

        self.lottery_running = False
        self.lottery_users = []
        self.lottery_points = 0

    def load_commands(self, **options):
        self.commands['pointlottery'] = pajbot.models.command.Command.raw_command(
                self.lottery,
                delay_all=0,
                delay_user=5,
                description='Lottery for points',
                examples=[
                    pajbot.models.command.CommandExample(
                        None,
                        'Lottery start',
                        chat='user:!pointlottery start\n'
                        'bot:A Lottery has begun. Type !pointlottery join {points} to join the lottery!',
                        description='Start lottery',
                        ).parse(),
                    pajbot.models.command.CommandExample(
                        None,
                        'Lottery join',
                        chat='user:!pointlottery join {}',
                        description='You don\'t get confirmation whether you joined the lottery or not.',
                        ).parse(),
                    pajbot.models.command.CommandExample(
                        None,
                        'Lottery stop',
                        chat='user:!pointlottery stop\n'
                        'bot:The lottery has finished! {} won {} points',
                        description='Finish lottery',
                        ).parse(),
                    pajbot.models.command.CommandExample(
                        None,
                        'Lottery join',
                        chat='user:!pointlottery {}',
                        description='You don\'t get confirmation whether you joined the lottery or not.',
                        ).parse(),
                ],
        )

    def lottery(self, **options):
        message = options['message']
        source = options['source']

        commands = {'start': (self.process_start, 500),
                    'begin': (self.process_start, 500),
                    'join': (self.process_join, 100),
                    '': (self.process_join, 100),
                    'end': (self.process_end, 500),
                    'stop': (self.process_end, 500),
                    'status': (self.process_status, 100),
                    }
        try:
            if message.split(' ')[0].isdigit():
                command = ''
            else:
                command = str(message.split(' ')[0])
            cb, level = commands[command]
            if source.level < level:
                # User does not have access to run this command
                return False
            cb(**options)
        except (KeyError, ValueError, TypeError, AttributeError):
            return False

    def process_start(self, **options):
        source = options['source']
        bot = options['bot']

        if self.lottery_running:
            bot.say('{0}, a lottery is already running OMGScoots'.format(source.username_raw))
            return False

        self.lottery_users = []
        self.lottery_running = True
        self.lottery_points = 0

        bot.websocket_manager.emit('notification', {'message': 'A lottery has been started!'})
        bot.execute_delayed(0.75, bot.websocket_manager.emit, ('notification',
                                                               {'message': 'Type !pointlottery join to enter!'}))

        bot.me('A lottery has begun. Type !pointlottery join {tickets} or !pointlottery {tickets} to join the lottery! '
               'The more tickets you buy, the more chances to win you have! '
               '1 ticket costs 1 point')

    def process_join(self, **options):
        source = options['source']
        message = options['message']
        bot = options['bot']

        if not self.lottery_running:
            log.debug('No lottery running')
            return False

        if source in [user for user, points in self.lottery_users if user == source]:
            return False

        try:
            if len(message.split(' ')) == 1:
                tickets = int(message.split(' ')[0])
            else:
                tickets = int(message.split(' ')[1])

            if not source.can_afford(tickets):
                bot.me('Sorry, {0}, you don\'t have enough points! FeelsBadMan'.format(source.username_raw))
                return False

            if tickets <= 0:
                bot.me('Sorry, {0}, you have to buy at least 1 ticket! FeelsBadMan'.format(source.username_raw))
                return False

            source.points -= tickets
            self.lottery_points += tickets
            log.info('Lottery points is now at {}'.format(self.lottery_points))
        except (ValueError, TypeError, AttributeError):
            bot.me('Sorry, {0}, I didn\'t recognize your command! FeelsBadMan'.format(source.username_raw))
            return False

        # Added user to the lottery
        self.lottery_users.append((source, tickets))

    def process_end(self, **options):
        bot = options['bot']

        if not self.lottery_running:
            return False

        self.lottery_running = False

        if not self.lottery_users:
            bot.me('Wow, no one joined the lottery DansGame')
            return False

        winner = self.weighted_choice(self.lottery_users)

        log.info('at end, lottery points is now at {}'.format(self.lottery_points))

        bot.websocket_manager.emit('notification', {'message': '{} won {} points in the lottery!'.format(
                winner.username_raw, self.lottery_points)})
        bot.me('The lottery has finished! {0} won {1} points! PogChamp'.format(winner.username_raw,
                                                                               self.lottery_points))

        winner.points += self.lottery_points

        winner.save()

        self.lottery_users = []

    def process_status(self, **options):
        bot = options['bot']

        if not self.lottery_running:
            return False

        bot.me('{} people have joined the lottery so far, for a total of {} points'.format(len(self.lottery_users),
                                                                                               self.lottery_points))

    @staticmethod
    def weighted_choice(choices):
        total = sum(w for c, w in choices)
        r = random.uniform(0, total)
        upto = 0
        for c, w in choices:
            if upto + w >= r:
                return c
            upto += w
        assert False, "Shouldn't get here"

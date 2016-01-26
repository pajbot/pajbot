import logging

from numpy import random

from pajbot.models.command import Command, CommandExample
from pajbot.modules.base import BaseModule

log = logging.getLogger(__name__)


class LotteryModule(BaseModule):
    ID = __name__.split('.')[-1]
    NAME = 'Lottery'
    DESCRIPTION = 'Lets players participate in lottery for points'
    SETTINGS = []

    def __init__(self):
        super().__init__()

        self.lottery_running = False
        self.lottery_users = []
        self.lottery_points = 0

    def load_commands(self, **options):
        self.commands['lottery'] = Command.raw_command(
                self.lottery,
                delay_all=0,
                delay_user=60,
                description='Lottery for points',
                examples=[
                    CommandExample(None,
                                   'Lottery start',
                                   chat='user:!lottery start\n'
                                        'bot:A Lottery has begun. Type !lottery join {points} to join the lottery!',
                                   description='Start lottery',
                                   ).parse(),
                    CommandExample(None,
                                   'Lottery join',
                                   chat='user:!lottery join {}',
                                   description='You don\'t get confirmation whether you joined the lottery or not.',
                                   ).parse(),
                    CommandExample(None,
                                   'Lottery end',
                                   chat='user:!lottery end\n'
                                        'bot:The lottery has finished! {} won {} points',
                                   description='Finish lottery',
                                   ).parse(),
                    CommandExample(None,
                                   'Lottery join',
                                   chat='user:!lottery {}',
                                   description='You don\'t get confirmation whether you joined the lottery or not.',
                                   ).parse(),
                ],
        )

    def lottery(self, **options):
        message = options['message']
        source = options['source']
        bot = options['bot']

        if source.level < 500:
            return False
        
        commands = {'start': self.process_start,
                    'join': self.process_join,
                    '': self.process_join,
                    'end': self.process_end,
                    }
        try:
            if message.split(' ')[0].isdigit():
                command = ''
            else:
                command = str(message.split(' ')[0])
            commands[command](**options)
        except (ValueError, TypeError, AttributeError):
            bot.me('Sorry, {0}, I didn\'t recognize your command! FeelsBadMan'.format(source.username_raw))
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
                                                               {'message': 'Type !lottery join to enter!'}))

        bot.me('A lottery has begun. Type !lottery join {tickets} or !lottery {tickets} to join the lottery! '
               'The more tickets you buy, the more chances to win you have! '
               '1 ticket costs 1 point')

    def process_join(self, **options):
        source = options['source']
        message = options['message']
        bot = options['bot']

        if not self.lottery_running:
            return False

        if source in [user for user in self.lottery_users if user == source]:
            return False

        try:
            if len(message.split(' ')) == 1:
                tickets = int(message.split(' ')[0])
            else:
                tickets = int(message.split(' ')[1])

            if source.points < tickets:
                bot.me('Sorry, {0}, you don\'t have enough points! FeelsBadMan'.format(source.username_raw))
                return False

            if tickets <= 0:
                bot.me('Sorry, {0}, you have to buy at least 1 ticket! FeelsBadMan'.format(source.username_raw))
                return False

            source.points -= tickets
            self.lottery_points += tickets
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

        bot.websocket_manager.emit('notification', {'message': '{} won {} points in the lottery!'.format(
                winner.username_raw, self.lottery_points)})
        bot.me('The lottery has finished! {0} won {1} points! PogChamp'.format(winner.username_raw,
                                                                               self.lottery_points))

        winner.points += self.lottery_points

        self.lottery_users = []

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

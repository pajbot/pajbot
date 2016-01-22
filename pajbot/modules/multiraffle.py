import logging
import datetime
import math

from pajbot.modules import BaseModule, ModuleSetting
from pajbot.models.command import Command, CommandExample
from pajbot.models.handler import HandlerManager
from pajbot.modules import RaffleModule

from numpy import random

log = logging.getLogger(__name__)

class MultiRaffleModule(BaseModule):

    ID = __name__.split('.')[-1]
    NAME = 'Multi Raffle (mini game)'
    DESCRIPTION = 'Split out points between multiple users'
    PARENT_MODULE = RaffleModule
    SETTINGS = []

    def load_commands(self, **options):
        self.commands['multiraffle'] = Command.raw_command(self.raffle,
                delay_all=0,
                delay_user=0,
                level=500,
                description='Start a raffle for points',
                examples=[
                    CommandExample(None, 'Start a raffle for 69 points',
                        chat='user:!raffle 69\n'
                        'bot:A raffle has begun for 69 points. Type !join to join the raffle! The raffle will end in in 60 seconds.',
                        description='Start a 60-second raffle for 69 points').parse(),
                    CommandExample(None, 'Start a raffle for the default value of {} points',
                        chat='user:!raffle 69 30\n'
                        'bot:A raffle has begun for 69 points. Type !join to join the raffle! The raffle will end in in 30 seconds.',
                        description='Start a 30-second raffle for 69 points').parse(),
                    ],
                )

    def raffle(self, **options):
        bot = options['bot']
        source = options['source']
        message = options['message']

        if self.parent_module.raffle_running is True:
            bot.say('{0}, a raffle is already running OMGScoots'.format(source.username_raw))
            return False

        self.parent_module.raffle_users = []
        self.parent_module.raffle_running = True
        self.parent_module.raffle_points = 100

        try:
            if message is not None:
                self.parent_module.raffle_points = int(message.split()[0])
        except ValueError:
            pass

        bot.websocket_manager.emit('notification', {'message': 'A raffle has been started!'})
        bot.execute_delayed(0.75, bot.websocket_manager.emit, ('notification', {'message': 'Type !join to enter!'}))

        bot.me('A multi-raffle has begun, {} points will be split among the winners. type !join to join the raffle! The raffle will end in 60 seconds'.format(self.parent_module.raffle_points))
        bot.execute_delayed(15, bot.me, ('The multi-raffle for {} points ends in 45 seconds! Type !join to join the raffle!'.format(self.parent_module.raffle_points), ))
        bot.execute_delayed(30, bot.me, ('The multi-raffle for {} points ends in 30 seconds! Type !join to join the raffle!'.format(self.parent_module.raffle_points), ))
        bot.execute_delayed(45, bot.me, ('The multi-raffle for {} points ends in 15 seconds! Type !join to join the raffle!'.format(self.parent_module.raffle_points), ))

        bot.execute_delayed(60, self.end_raffle)

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

        max_winners = 200
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
                num_winners = math.floor(abs_points / min_point_award)
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
        log.info(winners)
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

    def enable(self, bot):
        self.bot = bot

import logging

from pajbot.modules import BaseModule, ModuleSetting
from pajbot.modules import QuestModule
from pajbot.modules.quests import BaseQuest
from pajbot.managers import RedisManager
from pajbot.models.handler import HandlerManager
from pajbot.models.command import Command
from pajbot.streamhelper import StreamHelper

from numpy import random

log = logging.getLogger(__name__)

class WinDuelPointsQuestModule(BaseQuest):

    ID = 'quest-' + __name__.split('.')[-1]
    NAME = 'Win points in duels'
    DESCRIPTION = 'You need to win X amount of points in a duel to complete this quest.'
    PARENT_MODULE = QuestModule
    SETTINGS = [
            ModuleSetting(
                key='min_value',
                label='Minimum amount of points the user needs to win',
                type='number',
                required=True,
                placeholder='',
                default=250,
                constraints={
                    'min_value': 50,
                    'max_value': 2000,
                    }),
            ModuleSetting(
                key='max_value',
                label='Maximum amount of points the user needs to win',
                type='number',
                required=True,
                placeholder='',
                default=750,
                constraints={
                    'min_value': 100,
                    'max_value': 4000,
                    }),
                ]

    PROGRESS = 40
    LIMIT = 1
    REWARD = 7

    def __init__(self):
        super().__init__()
        # XXX: This key should probably be generic and always set in the BaseQuest
        self.points_required_key = '{streamer}:current_quest_points_required'.format(streamer=StreamHelper.get_streamer())
        # The points_required variable is randomized at the start of the quest.
        # It will be a value between settings['min_value'] and settings['max_value']
        self.points_required = None
        self.progress = {}

    def on_duel_complete(self, winner, loser, points_won, points_bet):
        if points_won < 1:
            # This duel did not award any points.
            # That means it's entirely irrelevant to us
            return

        if winner.username in self.progress:
            total_points_won = self.progress[winner.username]

            if total_points_won >= self.points_required:
                # The user has already won enough points, and been rewarded already.
                return
        else:
            total_points_won = 0

        # If we get here, this means the user has not completed the quest yet.
        # And the user won some points in this duel
        total_points_won += points_won

        redis = RedisManager.get()

        if total_points_won >= self.points_required:
            # Reward the user with some tokens
            winner.award_tokens(self.REWARD, redis=redis)

        # Save the users "points won" progress
        self.progress[winner.username] = total_points_won
        redis.hset(self.progress_key, winner.username, total_points_won)

    def start_quest(self):
        HandlerManager.add_handler('on_duel_complete', self.on_duel_complete)

        redis = RedisManager.get()

        self.progress = {}
        old_progress = redis.hgetall(self.progress_key)
        for user, progress in old_progress.items():
            try:
                self.progress[user.decode('utf8')] = int(progress)
            except (TypeError, ValueError):
                pass

        self.points_required = redis.get(self.points_required_key)
        try:
            self.points_required = int(self.points_required)
        except (TypeError, ValueError):
            pass
        if self.points_required is None:
            try:
                self.points_required = random.randint(self.settings['min_value'], self.settings['max_value'] + 1)
            except ValueError:
                # someone fucked up
                self.points_required = 500
            redis.set(self.points_required_key, self.points_required)

    def stop_quest(self):
        HandlerManager.remove_handler('on_duel_complete', self.on_duel_complete)

        redis = RedisManager.get()

        redis.delete(self.progress_key)
        redis.delete(self.points_required_key)

    def get_objective(self):
        return 'Make a profit of {} or more points in one or multiple duels.'.format(self.points_required)

    def enable(self, bot):
        self.bot = bot

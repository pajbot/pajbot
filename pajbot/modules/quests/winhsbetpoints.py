import logging

from numpy import random

from pajbot.managers.handler import HandlerManager
from pajbot.managers.redis import RedisManager
from pajbot.modules import ModuleSetting
from pajbot.modules import QuestModule
from pajbot.modules.quests import BaseQuest
from pajbot.streamhelper import StreamHelper

log = logging.getLogger(__name__)


class WinHsBetPointsQuestModule(BaseQuest):

    ID = 'quest-' + __name__.split('.')[-1]
    NAME = 'HsBet Points'
    DESCRIPTION = 'Win X points with Hearthstone bets.'
    PARENT_MODULE = QuestModule
    CATEGORY = 'Quest'
    SETTINGS = [
            ModuleSetting(
                key='min_value',
                label='Minimum amount of points the user needs to win',
                type='number',
                required=True,
                placeholder='',
                default=200,
                constraints={
                    'min_value': 25,
                    'max_value': 2000,
                    }),
            ModuleSetting(
                key='max_value',
                label='Maximum amount of points the user needs to win',
                type='number',
                required=True,
                placeholder='',
                default=650,
                constraints={
                    'min_value': 100,
                    'max_value': 4000,
                    })
            ]

    LIMIT = 1

    def __init__(self, bot):
        super().__init__(bot)
        self.hsbet_points_key = '{streamer}:current_quest_hsbet_points'.format(streamer=StreamHelper.get_streamer())
        self.hsbet_points_required = None
        self.progress = {}

    def on_user_win_hs_bet(self, user, points_reward):
        if points_reward < 1:
            return

        user_progress = self.get_user_progress(user.username, default=0)
        if user_progress >= self.hsbet_points_required:
            return

        user_progress += points_reward

        redis = RedisManager.get()

        if user_progress >= self.hsbet_points_required:
            self.finish_quest(redis, user)

        self.set_user_progress(user.username, user_progress, redis=redis)

    def start_quest(self):
        HandlerManager.add_handler('on_user_win_hs_bet', self.on_user_win_hs_bet)

        redis = RedisManager.get()

        self.load_progress(redis=redis)
        self.load_data(redis=redis)

        self.LIMIT = self.hsbet_points_required

    def load_data(self, redis=None):
        if redis is None:
            redis = RedisManager.get()

        self.hsbet_points_required = redis.get(self.hsbet_points_key)
        try:
            self.hsbet_points_required = int(self.hsbet_points_required)
        except (TypeError, ValueError):
            pass
        if self.hsbet_points_required is None:
            try:
                self.hsbet_points_required = random.randint(self.settings['min_value'], self.settings['max_value'] + 1)
            except ValueError:
                self.hsbet_points_required = 500
            redis.set(self.hsbet_points_key, self.hsbet_points_required)

    def stop_quest(self):
        HandlerManager.remove_handler('on_user_win_hs_bet', self.on_user_win_hs_bet)

        redis = RedisManager.get()

        self.reset_progress(redis=redis)
        redis.delete(self.hsbet_points_key)

    def get_objective(self):
        return 'Make a profit of {} or more points in one or multiple hearthstone bets.'.format(self.hsbet_points_required)

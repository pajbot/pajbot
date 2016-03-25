import logging

from pajbot.managers import RedisManager
from pajbot.models.handler import HandlerManager
from pajbot.modules import ModuleSetting
from pajbot.modules import QuestModule
from pajbot.modules.quests import BaseQuest

log = logging.getLogger(__name__)


class WinDuelsQuestModule(BaseQuest):

    ID = 'quest-' + __name__.split('.')[-1]
    NAME = 'Win duels'
    DESCRIPTION = 'Win X duels and make profit in every duel.'
    PARENT_MODULE = QuestModule
    CATEGORY = 'Quest'
    SETTINGS = [
            ModuleSetting(
                key='quest_limit',
                label='How many duels must a user win.',
                type='number',
                required=True,
                placeholder='',
                default=10,
                constraints={
                    'min_value': 1,
                    'max_value': 200,
                    })
            ]

    REWARD = 5

    def get_limit(self):
        return self.settings['quest_limit']

    def on_duel_complete(self, winner, loser, points_won, points_bet):
        if points_won < 1:
            return

        user_progress = self.get_user_progress(winner.username, default=0)
        if user_progress >= self.get_limit():
            return

        user_progress += 1

        redis = RedisManager.get()

        if user_progress == self.get_limit():
            winner.award_tokens(self.REWARD, redis=redis)

        self.set_user_progress(winner.username, user_progress, redis=redis)

    def start_quest(self):
        HandlerManager.add_handler('on_duel_complete', self.on_duel_complete)

        redis = RedisManager.get()

        self.load_progress(redis=redis)

    def stop_quest(self):
        HandlerManager.remove_handler('on_duel_complete', self.on_duel_complete)

        redis = RedisManager.get()

        self.reset_progress(redis=redis)

    def get_objective(self):
        return 'Win {} duels and make profit in every duel.'.format(self.get_limit())

    def enable(self, bot):
        self.bot = bot

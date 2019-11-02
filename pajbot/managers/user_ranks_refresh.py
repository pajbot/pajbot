import random

from sqlalchemy import text

from pajbot.managers.db import DBManager
from pajbot.managers.schedule import ScheduleManager
from pajbot.utils import time_method


class UserRanksRefreshManager:
    jitter = 60
    delay = 5 * 60

    @staticmethod
    def _jitter():
        return random.randint(0, UserRanksRefreshManager.jitter)

    @staticmethod
    def start(action_queue):
        # We add up to 1 minute of jitter to try to alleviate CPU spikes when multiple pajbot instances restart at the same time.
        # The jitter is added to both the initial refresh, and the scheduled one every 5 minutes.

        # Initial refresh
        ScheduleManager.execute_delayed(
            UserRanksRefreshManager._jitter(),
            lambda: action_queue.submit(UserRanksRefreshManager._refresh, action_queue),
        )

    @staticmethod
    @time_method
    def _refresh(action_queue):
        try:
            with DBManager.create_session_scope() as db_session:
                db_session.execute(text("REFRESH MATERIALIZED VIEW CONCURRENTLY user_rank"))
        finally:
            # Queue up the refresh in 5-6 minutes
            ScheduleManager.execute_delayed(
                UserRanksRefreshManager.delay + UserRanksRefreshManager._jitter(),
                lambda: action_queue.submit(UserRanksRefreshManager._refresh, action_queue),
            )

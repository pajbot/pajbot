import random

from sqlalchemy import text

from pajbot.managers.db import DBManager
from pajbot.managers.schedule import ScheduleManager
from pajbot.utils import time_method


class UserRanksRefreshManager:
    @staticmethod
    def start(action_queue):
        # We add ±30s of jitter to try to alleviate CPU spikes when multiple pajbot instances restart at the same time.
        # The jitter is added to both the initial refresh, and the scheduled one every 5 minutes.

        # Initial refresh
        ScheduleManager.execute_delayed(
            random.randint(0, 30), lambda: action_queue.submit(UserRanksRefreshManager._refresh)
        )

        # Run every 5 minutes, with each invocation scheduled ahead/past the 5 minute mark by a random value [-30, 30]
        ScheduleManager.execute_every(5 * 60, lambda: action_queue.submit(UserRanksRefreshManager._refresh), jitter=30)

    @staticmethod
    @time_method
    def _refresh():
        with DBManager.create_session_scope() as db_session:
            db_session.execute(text("REFRESH MATERIALIZED VIEW CONCURRENTLY user_rank"))

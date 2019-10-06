from sqlalchemy import text

from pajbot.managers.db import DBManager
from pajbot.managers.schedule import ScheduleManager
from pajbot.utils import time_method


class UserRanksRefreshManager:
    @staticmethod
    def start(action_queue):
        action_queue.submit(UserRanksRefreshManager._refresh)
        ScheduleManager.execute_every(5 * 60, lambda: action_queue.submit(UserRanksRefreshManager._refresh))

    @staticmethod
    @time_method
    def _refresh():
        with DBManager.create_session_scope() as db_session:
            db_session.execute(text("REFRESH MATERIALIZED VIEW CONCURRENTLY user_rank"))

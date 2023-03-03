import logging
import random

import pajbot.config as cfg
from pajbot.managers.db import DBManager
from pajbot.managers.schedule import ScheduleManager
from pajbot.utils import time_method

log = logging.getLogger(__name__)


class UserRanksRefreshManager:
    def __init__(self, config: cfg.Config) -> None:
        self.jitter = 60
        try:
            self.delay = int(config["main"].get("rank_refresh_delay", "5")) * 60
        except ValueError:
            log.exception("Bad rank_refresh_delay in your config")
            self.delay = 5 * 60

    def _jitter(self) -> int:
        return random.randint(0, self.jitter)

    def start(self, action_queue) -> None:
        # We add up to 1 minute of jitter to try to alleviate CPU spikes when multiple pajbot instances restart at the same time.
        # The jitter is added to both the initial refresh, and the scheduled one every 5 minutes.

        # Initial refresh
        ScheduleManager.execute_delayed(
            self._jitter(),
            lambda: action_queue.submit(self._refresh, action_queue),
        )

    def run_once(self, action_queue) -> None:
        # Initial refresh, run only once on startup
        ScheduleManager.execute_delayed(
            self._jitter() * 5,
            lambda: action_queue.submit(self._refresh, action_queue, once_only=True),
        )

    @time_method
    def _refresh(self, action_queue, once_only: bool = False) -> None:
        try:
            with DBManager.create_dbapi_cursor_scope(autocommit=True) as cursor:
                cursor.execute("REFRESH MATERIALIZED VIEW CONCURRENTLY user_rank")
                cursor.execute("VACUUM user_rank")
        finally:
            if once_only:
                return

            # Queue up the refresh in 5-6 minutes
            ScheduleManager.execute_delayed(
                self.delay + self._jitter(),
                lambda: action_queue.submit(UserRanksRefreshManager._refresh, action_queue),
            )

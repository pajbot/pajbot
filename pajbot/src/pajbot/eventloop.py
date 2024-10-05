from __future__ import annotations

from typing import Any, Callable, Union

import datetime
import logging
import numbers

from irc.schedule import IScheduler
from tempora import schedule
from tempora.schedule import Scheduler

log = logging.getLogger(__name__)


# same as InvokeScheduler from the original implementation,
# but with the extra try-catch
class SafeInvokeScheduler(Scheduler):
    """
    Command targets are functions to be invoked on schedule.
    """

    def run(self, command: schedule.DelayedCommand) -> None:
        try:
            command.target()
        except Exception:
            # we do "except Exception" to not catch KeyboardInterrupt and SystemExit (so the bot can properly quit)
            log.exception("Logging an uncaught exception (main thread)")


# same as DefaultScheduler from the original implementation,
# but extends SafeInvokeScheduler instead
class SafeDefaultScheduler(SafeInvokeScheduler, IScheduler):
    def execute_every(self, period: Union[float, datetime.timedelta], func: Callable[..., Any]) -> None:
        self.add(schedule.PeriodicCommand.after(period, func))

    def execute_at(self, when: Union[numbers.Real, datetime.datetime], func: Callable[..., Any]) -> None:
        self.add(schedule.DelayedCommand.at_time(when, func))

    def execute_after(self, delay: Union[float, datetime.timedelta], func: Callable[..., Any]) -> None:
        self.add(schedule.DelayedCommand.after(delay, func))

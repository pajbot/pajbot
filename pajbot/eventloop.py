import logging
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

    def run(self, command):
        try:
            command.target()
        except Exception:
            # we do "except Exception" to not catch KeyboardInterrupt and SystemExit (so the bot can properly quit)
            log.exception("Logging an uncaught exception (main thread)")


# same as DefaultScheduler from the original implementation,
# but extends SafeInvokeScheduler instead
class SafeDefaultScheduler(SafeInvokeScheduler, IScheduler):
    def execute_every(self, period, func):
        self.add(schedule.PeriodicCommand.after(period, func))

    def execute_at(self, when, func):
        self.add(schedule.DelayedCommand.at_time(when, func))

    def execute_after(self, delay, func):
        self.add(schedule.DelayedCommand.after(delay, func))

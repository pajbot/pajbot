import datetime
import logging

from pytz import timezone

log = logging.getLogger(__name__)


def is_naive_datetime(dt):
    return dt.tzinfo is None or dt.tzinfo.utcoffset(dt) is None


class TimeManager:
    timezone_object = None

    @staticmethod
    def init_timezone(timezone_str):
        TimeManager.timezone_object = timezone(timezone_str)

    @staticmethod
    def get_timezone():
        return TimeManager.timezone_object

    @staticmethod
    def localize(dt):
        """Localizes the given datetime into the display timezone.

        If the given datetime is naive, it is assumed to be of the UTC timezone.
        Non-naive datetimes will be directly converted to the target display timezone."""
        if is_naive_datetime(dt):
            log.warning(
                "Naive datetime passed to TimeManager#localize() (Naive datetimes should not be used in the bot anymore)"
            )
            input_dt = dt.replace(tzinfo=datetime.timezone.utc)
        else:
            input_dt = dt

        return input_dt.astimezone(TimeManager.get_timezone())

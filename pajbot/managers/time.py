import pytz
from pytz import timezone


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
        utc_dt = pytz.utc.localize(dt)
        return utc_dt.astimezone(TimeManager.get_timezone())

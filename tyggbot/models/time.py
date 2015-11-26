import pytz
from pytz import timezone

class TimeManager:
    timezone_object = None

    def init_timezone(timezone_str):
        TimeManager.timezone_object = timezone(timezone_str)

    def get_timezone():
        return TimeManager.timezone_object

    def localize(dt):
        utc_dt = pytz.utc.localize(dt)
        return utc_dt.astimezone(TimeManager.get_timezone())

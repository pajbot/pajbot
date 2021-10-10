import datetime

from .now import now
from .time_since import time_since


def time_ago(t: datetime.datetime, time_format: str = "long") -> str:
    return time_since(now().timestamp(), t.timestamp(), time_format=time_format)

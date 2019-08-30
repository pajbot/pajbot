from .time_since import time_since
from .now import now


def time_ago(t, time_format="long"):
    return time_since(now().timestamp(), t.timestamp(), time_format=time_format)

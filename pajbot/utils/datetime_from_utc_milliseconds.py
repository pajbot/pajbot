import datetime


def datetime_from_utc_milliseconds(ms):
    """Make a new timezone-aware datetime instance representing the timestamp
    `ms` milliseconds after the unix epoch at the UTC timezone (UTC milliseconds unix timestamp)."""
    return datetime.datetime.fromtimestamp(ms / 1000, tz=datetime.timezone.utc)

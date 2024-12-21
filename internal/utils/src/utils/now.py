import datetime


def now() -> datetime.datetime:
    """
    Returns a timezone-aware datetime object representing the current universal coordinated time (UTC).
    E.g.: datetime.datetime(2019, 5, 31, 14, 36, 49, 861063, tzinfo=datetime.timezone.utc)

    A UTC unix timestamp (in seconds) can be obtained by calling .timestamp() on the object
    returned by this function.

    :return: The datetime object
    """
    return datetime.datetime.utcnow().replace(tzinfo=datetime.timezone.utc)

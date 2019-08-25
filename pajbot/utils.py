import datetime
import logging
import math
import signal
import sys
from contextlib import contextmanager

from colorama import Fore
from colorama import Style

import pajbot.exc

log = logging.getLogger(__name__)


def now():
    """
    Returns a timezone-aware datetime object representing the current universal coordinated time (UTC).
    E.g.: datetime.datetime(2019, 5, 31, 14, 36, 49, 861063, tzinfo=datetime.timezone.utc)

    A UTC unix timestamp (in seconds) can be obtained by calling .timestamp() on the object
    returned by this function.

    :return: The datetime object
    """
    return datetime.datetime.utcnow().replace(tzinfo=datetime.timezone.utc)


def datetime_from_utc_milliseconds(ms):
    """Make a new timezone-aware datetime instance representing the timestamp
    `ms` milliseconds after the unix epoch at the UTC timezone (UTC milliseconds unix timestamp)."""
    return datetime.datetime.fromtimestamp(ms / 1000, tz=datetime.timezone.utc)


def time_method(f):
    import inspect

    def get_class_that_defined_method(meth):
        if inspect.ismethod(meth):
            for cls in inspect.getmro(meth.__self__.__class__):
                if cls.__dict__.get(meth.__name__) is meth:
                    return cls
            meth = meth.__func__
        if inspect.isfunction(meth):
            cls = getattr(inspect.getmodule(meth), meth.__qualname__.split(".<locals>", 1)[0].rsplit(".", 1)[0])
            if isinstance(cls, type):
                return cls
        return None

    def wrap(*args):
        time1 = now().timestamp()
        ret = f(*args)
        time2 = now().timestamp()
        log.debug(
            "{0.__name__}::{1.__name__} function took {2:.3f} ms".format(
                get_class_that_defined_method(f), f, (time2 - time1) * 1000.0
            )
        )
        return ret

    return wrap


def time_nonclass_method(f):
    def wrap(*args):
        time1 = now().timestamp()
        ret = f(*args)
        time2 = now().timestamp()
        log.debug("{0.__name__} function took {1:.3f} ms".format(f, (time2 - time1) * 1000.0))
        return ret

    return wrap


@contextmanager
def profile_timer(name):
    time1 = now().timestamp()
    yield
    time2 = now().timestamp()
    log.debug('"{0}" task took {1:.3f} ms'.format(name, (time2 - time1) * 1000.0))


def find(predicate, seq):
    """Method shamelessly taken from https://github.com/Rapptz/discord.py """

    for element in seq:
        if predicate(element):
            return element
    return None


def remove_none_values(d):
    return {k: v for k, v in d.items() if v is not None}


ALLIN_PHRASES = ("all", "allin")


def parse_points_amount(user, point_string):
    if point_string.startswith("0b"):
        try:
            bet = int(point_string, 2)

            return bet
        except (ValueError, TypeError):
            raise pajbot.exc.InvalidPointAmount("Invalid binary format (example: 0b101)")
    elif point_string.startswith("0x"):
        try:
            bet = int(point_string, 16)

            return bet
        except (ValueError, TypeError):
            raise pajbot.exc.InvalidPointAmount("Invalid hex format (example: 0xFF)")
    elif point_string.endswith("%"):
        try:
            percentage = float(point_string[:-1])
            if percentage <= 0 or percentage > 100:
                raise pajbot.exc.InvalidPointAmount("Invalid percentage format (example: 43.5%) :o")

            return math.floor(user.points_available() * (percentage / 100))
        except (ValueError, TypeError):
            raise pajbot.exc.InvalidPointAmount("Invalid percentage format (example: 43.5%)")
    elif point_string[0].isnumeric():
        try:
            point_string = point_string.lower()
            num_k = point_string.count("k")
            num_m = point_string.count("m")
            point_string = point_string.replace("k", "")
            point_string = point_string.replace("m", "")
            bet = float(point_string)

            if num_k:
                bet *= 1000 ** num_k
            if num_m:
                bet *= 1000000 ** num_m

            return round(bet)
        except (ValueError, TypeError):
            raise pajbot.exc.InvalidPointAmount("Non-recognizable point amount (examples: 100, 10k, 1m, 0.5k)")
    elif point_string.lower() in ALLIN_PHRASES:
        return user.points_available()

    raise pajbot.exc.InvalidPointAmount("Invalid point amount (examples: 100, 10k, 1m, 0.5k)")


def print_traceback():
    import traceback

    traceback.print_stack()


def time_since(t1, t2, time_format="long"):
    time_diff = t1 - t2
    if time_format == "long":
        num_dict = ["year", "month", "day", "hour", "minute", "second"]
    else:
        num_dict = ["y", "M", "d", "h", "m", "s"]
    num = [
        math.trunc(time_diff / 31536000),
        math.trunc(time_diff / 2628000 % 12),
        math.trunc(time_diff / 86400 % 30.41666666666667),
        math.trunc(time_diff / 3600 % 24),
        math.trunc(time_diff / 60 % 60),
        round(time_diff % 60, 1),
    ]

    i = 0
    j = 0
    time_arr = []
    while i < 2 and j < 6:
        if num[j] > 0:
            if time_format == "long":
                time_arr.append("{0:g} {1}{2}".format(num[j], num_dict[j], "s" if num[j] > 1 else ""))
            else:
                time_arr.append("{}{}".format(num[j], num_dict[j]))
            i += 1
        j += 1

    if time_format == "long":
        return " and ".join(time_arr)

    return "".join(time_arr)


def time_ago(t, time_format="long"):
    return time_since(now().timestamp(), t.timestamp(), time_format=time_format)


def tweet_prettify_urls(tweet):
    tweet_text = tweet.text
    for url in tweet.entities["urls"]:
        tweet_text = tweet_text.replace(url["url"], url["expanded_url"])

    return tweet_text


def load_config(path):
    import configparser
    import os

    config = configparser.ConfigParser()
    config.read_dict({"main": {"trusted_mods": "0"}, "web": {"deck_tab_images": "1"}})

    res = config.read(os.path.realpath(path))

    if not res:
        log.error("%s missing. Check out the example config file.", path)
        sys.exit(0)

    return config


@contextmanager
def time_limit(seconds):
    def signal_handler(signum, frame):
        raise pajbot.exc.TimeoutException("Timed out!")

    signal.signal(signal.SIGALRM, signal_handler)
    signal.alarm(seconds)
    try:
        yield
    finally:
        signal.alarm(0)


def init_logging(app="pajbot"):
    class LogFilter(logging.Filter):
        def __init__(self, level):
            super().__init__()
            self.level = level

        def filter(self, record):
            return record.levelno < self.level

    colors = {
        "WARNING": Fore.YELLOW,
        "INFO": Fore.WHITE,
        "DEBUG": Fore.BLUE,
        "CRITICAL": Fore.YELLOW,
        "ERROR": Fore.RED,
    }

    class ColoredFormatter(logging.Formatter):
        def __init__(self, msg):
            logging.Formatter.__init__(self, msg)

        def format(self, record):
            levelname = record.levelname
            if levelname in colors:
                levelname_color = Style.BRIGHT + colors[levelname] + levelname + Style.RESET_ALL
                record.levelname = levelname_color
            return logging.Formatter.format(self, record)

    # Uncomment the line below if you want full debug messages from everything!
    # This includes all debug messages from the IRC libraries, which can be useful for debugging.
    # logging.basicConfig(level=logging.DEBUG - 2)

    logger = logging.getLogger(app)
    logger.setLevel(logging.DEBUG)

    colored_formatter = ColoredFormatter("[%(asctime)s] [%(levelname)-20s] %(message)s")
    log_filter = LogFilter(logging.WARNING)

    logger_stdout = logging.StreamHandler(sys.stdout)
    logger_stdout.setFormatter(colored_formatter)
    logger_stdout.addFilter(log_filter)
    logger_stdout.setLevel(logging.DEBUG)

    logger_stderr = logging.StreamHandler(sys.stderr)
    logger_stderr.setFormatter(colored_formatter)
    logger_stderr.setLevel(logging.WARNING)

    logging.getLogger().addHandler(logger_stdout)
    logging.getLogger().addHandler(logger_stderr)

    return logger


def clean_up_message(message):
    # list of twitch commands permitted, without leading slash or dot
    permitted_commands = ["me"]

    # remove leading whitespace
    message = message.lstrip()

    # limit of one split
    # '' -> ['']
    # 'a' -> ['a']
    # 'a ' -> ['a', '']
    # 'a b' -> ['a', 'b']
    # 'a b ' -> ['a', 'b ']
    # 'a b c' -> ['a', 'b c']
    parts = message.split(" ", 1)

    # if part 0 is a twitch command, we determine command and payload.
    if parts[0][:1] in [".", "/"]:
        if parts[0][1:] in permitted_commands:
            # permitted twitch command
            command = parts[0]
            if len(parts) < 2:
                payload = None
            else:
                payload = parts[1].lstrip()
        else:
            # disallowed twitch command
            command = "."
            payload = message
    else:
        # not a twitch command
        command = None
        payload = message

    # Stop the bot from calling other bot commands
    # by prefixing payload with invisible character
    if payload[:1] in ["!", "$", "-", "<"]:
        payload = "\U000e0000" + payload

    if command is not None and payload is not None:
        # we have command and payload (e.g. ".me asd" or ". .timeout")
        return "{} {}".format(command, payload)

    if command is not None:
        # we have command and NO payload (e.g. ".me")
        return command

    # we have payload and NO command (e.g. "asd", "\U000e0000!ping")
    return payload


def iterate_split_with_index(split_parts, separator_length=1):
    """Generator function that for a given list of split parts of a string,
    returns a tuple with the starting index of that split word/part (in the original string) and the part"""
    index = 0
    for part in split_parts:
        yield index, part
        index += len(part) + separator_length


def dump_threads():
    import threading
    import traceback

    for th in threading.enumerate():
        print(th)
        traceback.print_stack(sys._current_frames()[th.ident])
        print()


def split_into_chunks_with_prefix(chunks, separator=" ", limit=500, default=None):
    messages = []
    current_message = ""
    current_prefix = None

    def try_append(prefix, new_part, recursive=False):
        nonlocal messages
        nonlocal current_message
        nonlocal current_prefix
        needs_prefix = current_prefix != prefix
        # new_suffix is the thing we want to append to the current_message
        new_suffix = prefix + separator + new_part if needs_prefix else new_part
        if len(current_message) > 0:
            new_suffix = separator + new_suffix

        if len(current_message) + len(new_suffix) <= limit:
            # fits
            current_message += new_suffix
            current_prefix = prefix
        else:
            # doesn't fit, start new message
            if recursive:
                raise ValueError("Function was given part that could never fit")

            messages.append(current_message)
            current_message = ""
            current_prefix = None
            try_append(prefix, new_part, True)

    for chunk in chunks:
        prefix = chunk["prefix"]
        parts = chunk["parts"]
        for part in parts:
            try_append(prefix, part)

    if len(current_message) > 0:
        messages.append(current_message)

    if len(messages) <= 0 and default is not None:
        messages = [default]

    return messages

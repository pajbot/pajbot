import logging
import threading
import signal
import math
import sys
import time
import datetime

from colorama import Fore, Style
from contextlib import contextmanager

log = logging.getLogger('pajbot')

COLORS = {
    'WARNING': Fore.YELLOW,
    'INFO': Fore.WHITE,
    'DEBUG': Fore.BLUE,
    'CRITICAL': Fore.YELLOW,
    'ERROR': Fore.RED
}


class ColoredFormatter(logging.Formatter):
    def __init__(self, msg):
        logging.Formatter.__init__(self, msg)

    def format(self, record):
        levelname = record.levelname
        if levelname in COLORS:
            levelname_color = Style.BRIGHT + COLORS[levelname] + levelname + Style.RESET_ALL
            record.levelname = levelname_color
        return logging.Formatter.format(self, record)


def init_logging(app='pajbot'):
    class LogFilter(logging.Filter):
        def __init__(self, level):
            self.level = level

        def filter(self, record):
            return record.levelno < self.level

    # Uncomment the line below if you want full debug messages from everything!
    # This includes all debug messages from the IRC libraries, which can be useful for debugging.
    # logging.basicConfig(level=logging.DEBUG)

    log = logging.getLogger(app)
    log.setLevel(logging.DEBUG)

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

    return log


class LogThread(threading.Thread):
    """LogThread should always e used in preference to threading.Thread.

    The interface provided by LogThread is identical to that of threading.Thread,
    however, if an exception occurs in the thread the error will be logged
    (using logging.exception) rather than printed to stderr.

    This is important in daemon style applications where stderr is redirected
    to /dev/null.

    """
    def __init__(self, on_exception, **kwargs):
        super().__init__(**kwargs)
        self._real_run = self.run
        self.run = self._wrap_run
        self.on_exception = on_exception

    def _wrap_run(self):
        try:
            self._real_run()
        except Exception as e:
            self.on_exception(e)


class TimeoutException(Exception):
    pass


@contextmanager
def time_limit(seconds):
    def signal_handler(signum, frame):
        raise TimeoutException("Timed out!")
    signal.signal(signal.SIGALRM, signal_handler)
    signal.alarm(seconds)
    try:
        yield
    finally:
        signal.alarm(0)


class SyncValue:
    def __init__(self, value, synced=False):
        self.value = value
        self.synced = synced

    def increment(self, step=1):
        self.value += step
        self.synced = False


def time_since(t1, t2, format='long'):
    time_diff = t1 - t2
    if format == 'long':
        num_dict = ['year', 'month', 'day', 'hour', 'minute', 'second']
    else:
        num_dict = ['y', 'M', 'd', 'h', 'm', 's']
    num = [math.trunc(time_diff / 31536000),
           math.trunc(time_diff / 2628000 % 12),
           math.trunc(time_diff / 86400 % 30.41666666666667),
           math.trunc(time_diff / 3600 % 24),
           math.trunc(time_diff / 60 % 60),
           round(time_diff % 60, 1)]

    i = 0
    j = 0
    time_arr = []
    while i < 2 and j < 6:
        if num[j] > 0:
            if format == 'long':
                time_arr.append('{0:g} {1}{2}'.format(num[j], num_dict[j], 's' if num[j] > 1 else ''))
            else:
                time_arr.append('{0}{1}'.format(num[j], num_dict[j]))
            i += 1
        j += 1

    if format == 'long':
        return ' and '.join(time_arr)
    else:
        return ''.join(time_arr)


def time_ago(dt, format='long'):
    return time_since(datetime.datetime.now().timestamp(), dt.timestamp(), format=format)


def tweet_prettify_urls(tweet):
    tw = tweet.text
    for u in tweet.entities['urls']:
        tw = tw.replace(u['url'], u['expanded_url'])

    return tw


def load_config(path):
    import configparser
    import os
    defaults = {
            'add_self_as_whisper_account': '1',
            'trusted_mods': '0',
            'deck_tab_images': '1',
            }
    config = configparser.ConfigParser(defaults=defaults)

    res = config.read(os.path.realpath(path))

    if len(res) == 0:
        log.error('{0} missing. Check out install/config.example.ini'.format(path))
        sys.exit(0)

    return config


def create_insert_query(table, values):
    value_keys = ','.join(['`{}`'.format(x) for x in values])
    value_values = ','.join(['%s' for x in values])
    return 'INSERT INTO `{table}` ({value_keys}) VALUES ({value_values})'.format(table=table, value_keys=value_keys, value_values=value_values)


def create_update_query(table, values, extra=''):
    values_formatted = ','.join(['`{}`=%s'.format(x) for x in values])
    return 'UPDATE `{table}` SET {values_formatted} {extra}'.format(table=table, values_formatted=values_formatted, extra=extra)

def time_method(f):
    import inspect

    def get_class_that_defined_method(meth):
        if inspect.ismethod(meth):
            for cls in inspect.getmro(meth.__self__.__class__):
                if cls.__dict__.get(meth.__name__) is meth:
                    return cls
            meth = meth.__func__
        if inspect.isfunction(meth):
            cls = getattr(inspect.getmodule(meth),
                          meth.__qualname__.split('.<locals>', 1)[0].rsplit('.', 1)[0])
            if isinstance(cls, type):
                return cls
        return None

    def wrap(*args):
        time1 = time.time()
        ret = f(*args)
        time2 = time.time()
        log.debug('{0.__name__}::{1.__name__} function took {2:.3f} ms'.format(get_class_that_defined_method(f), f, (time2 - time1) * 1000.0))
        return ret
    return wrap

def time_nonclass_method(f):
    def wrap(*args):
        time1 = time.time()
        ret = f(*args)
        time2 = time.time()
        log.debug('{0.__name__} function took {1:.3f} ms'.format(f, (time2 - time1) * 1000.0))
        return ret
    return wrap

def print_traceback():
    import traceback
    traceback.print_stack()

def find(predicate, seq):
    """Method shamelessly taken from https://github.com/Rapptz/discord.py """

    for element in seq:
        if predicate(element):
            return element
    return None

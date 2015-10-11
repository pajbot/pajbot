import logging
import threading
import signal
import math
import sys

from colorama import Fore, Style
from contextlib import contextmanager

log = logging.getLogger('tyggbot')

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


def init_logging(app='tyggbot'):
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
        num_dict = ['day', 'hour', 'minute', 'second']
    else:
        num_dict = ['d', 'h', 'm', 's']
    num = [math.trunc(time_diff / 86400),
           math.trunc(time_diff / 3600 % 24),
           math.trunc(time_diff / 60 % 60),
           round(time_diff % 60, 1)]

    i = 0
    j = 0
    time_arr = []
    while i < 2 and j < 4:
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


def tweet_prettify_urls(tweet):
    tw = tweet.text
    for u in tweet.entities['urls']:
        tw = tw.replace(u['url'], u['expanded_url'])

    return tw


def load_config(path):
    import configparser
    import os
    config = configparser.ConfigParser()

    configfile = os.path.dirname(os.path.realpath(__file__)) + '/' + path
    res = config.read(configfile)

    if len(res) == 0:
        log.error('{0} missing. Check out install/config.example.ini'.format(path))
        sys.exit(0)

    return config

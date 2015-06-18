import os, logging, threading, signal, math

from colorama import Fore, Back, Style
from contextlib import contextmanager

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

def init_logging(filename, app='tyggbot'):
    base_path = os.path.dirname(os.path.realpath(__file__))
    log = logging.getLogger(app)
    log.setLevel(logging.DEBUG)

    fh = logging.FileHandler(base_path + '/' + filename)
    fh.setFormatter(logging.Formatter('%(asctime)-24s [%(levelname)-7s] %(message)s'))

    ch = logging.StreamHandler()
    ch.setFormatter(ColoredFormatter("[%(levelname)-20s] %(message)s"))

    logging.getLogger(app).addHandler(fh)
    logging.getLogger(app).addHandler(ch)

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
            #logging.exception('Exception during LogThread.run')

class TimeoutException(Exception): pass

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

def time_since(t1, t2):
    time_diff = t1 - t2
    num_dict = ['day', 'hour', 'minute', 'second']
    num = [math.trunc(time_diff / 86400),
           math.trunc(time_diff / 3600 % 24),
           math.trunc(time_diff / 60 % 60),
           math.trunc(time_diff % 60)]

    i = 0
    j = 0
    time_arr = []
    while i < 2 and j < 4:
        if num[j] > 0:
            time_arr.append('{0} {1}{2}'.format(num[j], num_dict[j], 's' if num[j] > 1 else ''))
            i += 1
        j += 1

    return ' and '.join(time_arr)

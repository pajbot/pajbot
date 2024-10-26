from typing import Any, Iterator

import signal
from contextlib import contextmanager

from pajbot.exc import TimeoutException


@contextmanager
def time_limit(seconds: int) -> Iterator[None]:
    def signal_handler(signum: Any, frame: Any) -> None:
        raise TimeoutException("Timed out!")

    signal.signal(signal.SIGALRM, signal_handler)
    signal.alarm(seconds)
    try:
        yield
    finally:
        signal.alarm(0)

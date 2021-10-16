from __future__ import annotations

from typing import Any, Callable, TypeVar

import logging
from concurrent.futures import Future
from concurrent.futures.thread import ThreadPoolExecutor

_T = TypeVar("_T")

log = logging.getLogger(__name__)


# This implementation is functionally identical to using the ThreadPoolExecutor directly,
# but it adds the callback, to log uncaught exceptions.
class ActionQueue:
    def __init__(self) -> None:
        self.thread_pool_executor = ThreadPoolExecutor()

    def submit(self, function: Callable[..., _T], *args: Any, **kwargs: Any) -> Future[_T]:
        future = self.thread_pool_executor.submit(function, *args, **kwargs)
        future.add_done_callback(self._on_future_done)
        return future

    def _on_future_done(self, future: Future[_T]) -> None:
        exc = future.exception()
        if exc is not None:
            log.exception("Logging an uncaught exception (ActionQueue)", exc_info=exc)

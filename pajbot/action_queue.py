from concurrent.futures.thread import ThreadPoolExecutor

import logging

log = logging.getLogger(__name__)


# This implementation is functionally identical to using the ThreadPoolExecutor directly,
# but it adds the callback, to log uncaught exceptions.
class ActionQueue:
    def __init__(self):
        self.thread_pool_executor = ThreadPoolExecutor()

    def submit(self, function, *args, **kwargs):
        future = self.thread_pool_executor.submit(function, *args, **kwargs)
        future.add_done_callback(self._on_future_done)
        return future

    def _on_future_done(self, future):
        exc = future.exception()
        if exc is not None:
            log.exception("Logging an uncaught exception (ActionQueue)", exc_info=exc)

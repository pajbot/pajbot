import logging
import threading
from datetime import datetime, timedelta

log = logging.getLogger('pajbot')


class CachedValue:
    """Keep a value cached and update as needed."""

    def __init__(self, duration=60, update_method=None, update_method_type='direct', update_method_args=()):
        """
        Keyword arguments:
        duration -- how long the value should be cached in seconds (default=60)
        """
        self.duration = timedelta(seconds=duration)
        self.update_method = update_method
        self.update_method_type = update_method_type
        self.update_method_args = update_method_args
        self.last_update = None
        self.event = threading.Event()
        self.value = None

    def set_update_method(self, method, type='direct'):
        """ An update method of type `direct` will do something similar to this:
        self.value = method()

        Whereas an update method of type `indirect` will simply call the method like this:
        method() and expect the value to be updated properly in the method itself.
        """
        self.update_method = method

    def get(self):
        """ Returns the requested value.
        Will return the cached value if possible, otherwise it will run the update method
        and return the fresh value when possible.
        """
        now = datetime.now()
        if self.value is None or self.last_update is None or now - self.last_update > self.duration:
            self.value = None
            log.debug('Waiting for CachedValue event.')
            self.update_method(*self.update_method_args)
            event_value = self.event.wait(1)
            log.debug('Waited for event: {0}'.format(event_value))
            log.debug('Value is now: {0}'.format(self.value))

        return self.value

    def set(self, value):
        self.last_update = datetime.now()
        self.value = value
        self.event.set()

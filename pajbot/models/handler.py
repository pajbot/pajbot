import operator
import logging

log = logging.getLogger('pajbot')

class HandlerManager:
    handlers = {}

    def init_handlers():
        HandlerManager.handlers = {}

        # on_pubmsg(source, message)
        HandlerManager.create_handler('on_pubmsg')

        # on_message(source, message, emotes, whisper, urls)
        HandlerManager.create_handler('on_message')

        # on_commit()
        HandlerManager.create_handler('on_commit')

        # on_stream_start()
        HandlerManager.create_handler('on_stream_start')

        # on_paid_timeout(source, victim)
        HandlerManager.create_handler('on_paid_timeout')

    def create_handler(event):
        """ Create an empty list for the given event """
        HandlerManager.handlers[event] = []

    def add_handler(event, method, priority=0):
        try:
            HandlerManager.handlers[event].append((method, priority))
            HandlerManager.handlers[event].sort(key=operator.itemgetter(1), reverse=True)
        except KeyError:
            # No handlers for this event found
            pass

    def remove_handler(event, method):
        try:
            HandlerManager.handlers[event][:] = [h for h in HandlerManager.handlers[event] if h[0] is method]
        except KeyError:
            # No handlers for this event found
            pass

    def trigger(event, *arguments, stop_on_false=True):
        if event not in HandlerManager.handlers:
            log.error('No handler set for event {}'.format(event))
            return False

        for handler, priority in HandlerManager.handlers[event]:
            res = None
            try:
                res = handler(*arguments)
            except:
                log.exception('Unhandled exception from {} in on_message'.format(handler))

            if res is False and stop_on_false is True:
                # Abort if handler returns false and stop_on_false is enabled
                return False

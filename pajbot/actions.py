import logging
import queue
import threading

log = logging.getLogger(__name__)


class Action:
    func = None
    args = []
    kwargs = {}

    def __init__(self, func=None, args=[], kwargs={}):
        self.func = func
        self.args = args
        self.kwargs = kwargs

    def run(self):
        self.func(*self.args, **self.kwargs)


class ActionQueue:
    ID = 0

    def __init__(self):
        self.queue = queue.Queue()
        self.id = ActionQueue.ID
        ActionQueue.ID += 1

    # Starts a thread which will continuously check the queue for actions.

    def start(self):
        t = threading.Thread(target=self._action_parser, name="ActionQueueThread_{}".format(self.id))
        t.daemon = True
        t.start()

    # Start a loop which waits and things to be added into the queue.
    # Note: This is a blocking method, and should be run in a separate thread
    # This method is started automatically if ActionQueue is declared threaded.

    def _action_parser(self):
        while True:
            action = self.queue.get()
            try:
                action.run()
            except:
                log.exception("Logging an uncaught exception (ActionQueue)")

    # Run a single action in the queue if the queue is not empty.

    def parse_action(self):
        if not self.queue.empty():
            action = self.queue.get()
            action.run()

    def add(self, func, args=[], kwargs={}):
        action = Action(func, args, kwargs)
        self._add(action)

    def _add(self, action):
        self.queue.put(action)

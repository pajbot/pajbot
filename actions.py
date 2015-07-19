import queue
import threading

class Action:
    func = None
    args = []
    kwargs = {}

    def __init__(self, f=None, args=[], kwargs={}):
        self.func = f
        self.args = args
        self.kwargs = kwargs
        return

class ActionQueue:
    def __init__(self):
        self.Q = queue.Queue()
        t = threading.Thread(target=self.action_parser)
        t.start()

    def action_parser(self):
        while True:
            action = self.Q.get()
            action.func(*action.args, **action.kwargs)

    def add(self, f, args=[], kwargs={}):
        action = Action()
        action.func = f

        action.args = args
        action.kwargs = kwargs
        self._add(action)

    def _add(self, action):
        self.Q.put(action)

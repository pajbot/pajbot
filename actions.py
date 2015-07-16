import queue
import threading

class Action:
    func = None
    args = []
    kwargs = {}

    def __init__(self):
        return

class ActionQueue:
    def __init__(self):
        self.Q = queue.Queue()
        t = threading.Thread(target=self.action_parser)
        t.start()

    def action_parser(self):
        while True:
            action = self.Q.get()
            if action.args is None: action.args = []
            if action.kwargs is None: action.kwargs = {}
            action.func(*action.args, **action.kwargs)

    def add(self, f, args=None, kwargs=None):
        action = Action()
        action.func = f

        action.args = args
        action.kwargs = kwargs
        self._add(action)

    def _add(self, action):
        self.Q.put(action)

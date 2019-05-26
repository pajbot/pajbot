import json
import logging
import threading

from pajbot.managers.redis import RedisManager

log = logging.getLogger(__name__)


class SocketManager:
    def __init__(self):
        self.handlers = {}
        self.pubsub = RedisManager.get().pubsub()
        self.running = True

        self.pubsub.subscribe('test')  # need this for keepalive? idk

        self.thread = threading.Thread(target=self.start, name='SocketManagerThread')
        self.thread.daemon = True
        self.thread.start()

    def quit(self):
        self.running = False

    def add_handler(self, topic, method):
        if topic not in self.handlers:
            self.handlers[topic] = [method]
            self.pubsub.subscribe(topic)
        else:
            self.handlers[topic].append(method)

    def start(self):
        while self.running:
            message = self.pubsub.get_message(ignore_subscribe_messages=True, timeout=1)
            if not message:
                continue

            if message['channel'] not in self.handlers:
                continue

            for handler in self.handlers[message['channel']]:
                handler(json.loads(message['data']))

        self.pubsub.close()


class SocketClientManager:
    sock_file = None

    @staticmethod
    def init(sock_file):
        SocketClientManager.sock_file = sock_file

    @staticmethod
    def send(topic, data):
        RedisManager.publish(topic, json.dumps(data))

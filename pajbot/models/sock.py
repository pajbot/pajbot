from typing import Any, Callable, Dict, List, Optional

import json
import logging
import threading

from pajbot.managers.redis import RedisManager

log = logging.getLogger(__name__)

HandlerParam = Dict[str, Any]
Handler = Callable[[HandlerParam], None]


class SocketManager:
    def __init__(self, streamer_name: str, callback: Callable[[Handler, Any], None]) -> None:
        self.handlers: Dict[str, List[Handler]] = {}
        self.pubsub = RedisManager.get().pubsub()
        self.running = True
        self.streamer_name = streamer_name
        self.callback = callback

        self.pubsub.subscribe("test")  # need this for keepalive? idk

        self.thread = threading.Thread(target=self.start, name="SocketManagerThread")
        self.thread.daemon = True
        self.thread.start()

    def quit(self) -> None:
        self.running = False

    def add_handler(self, topic: str, method: Handler) -> None:
        topic = f"{self.streamer_name}:{topic}"

        if topic not in self.handlers:
            self.handlers[topic] = [method]
            self.pubsub.subscribe(topic)
        else:
            self.handlers[topic].append(method)

    def start(self) -> None:
        while self.running:
            message = self.pubsub.get_message(ignore_subscribe_messages=True, timeout=1)
            if not message:
                continue

            if message["channel"] not in self.handlers:
                continue

            try:
                parsed_data = json.loads(message["data"])
            except json.decoder.JSONDecodeError:
                log.exception("Bad JSON data on %s topic: '%s'", message["channel"], message["data"])
                continue

            for handler in self.handlers[message["channel"]]:
                # invokes the handler on the bot's main thread (the IRC event loop)
                self.callback(handler, parsed_data)

        self.pubsub.close()


class SocketClientManager:
    streamer_name: Optional[str] = None

    @classmethod
    def init(cls, streamer_name: str) -> None:
        cls.streamer_name = streamer_name

    @classmethod
    def send(cls, topic: str, data: Any) -> bool:
        if cls.streamer_name is None:
            raise ValueError("streamer_name not set in SocketClientManager")

        topic = f"{cls.streamer_name}:{topic}"

        return RedisManager.publish(topic, json.dumps(data)) > 0

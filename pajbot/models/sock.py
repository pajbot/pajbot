from typing import Any, Callable, Optional

import json
import logging

from pajbot.managers.redis import RedisManager
import redis.asyncio.client

log = logging.getLogger(__name__)

HandlerParam = dict[str, Any]
Handler = Callable[[HandlerParam], None]


class SocketManager:
    def __init__(self, streamer_name: str) -> None:
        self.handlers: dict[str, list[Handler]] = {}
        self.streamer_name = streamer_name

    def add_handler(self, topic: str, method: Handler) -> None:
        topic = f"{self.streamer_name}:{topic}"

        if topic not in self.handlers:
            self.handlers[topic] = [method]
            # await self.pubsub.subscribe(topic)
        else:
            self.handlers[topic].append(method)

    async def reader(self, channel: redis.asyncio.client.PubSub) -> None:
        log.info("redis reader start")
        while True:
            message = await channel.get_message(ignore_subscribe_messages=True)
            if message is not None:
                log.debug(f"Redis PubSub message received: {message}")

                if message["channel"] in self.handlers:
                    if message["channel"] not in self.handlers:
                        log.info(f"No handler for {message['channel']}")
                        continue

                    try:
                        parsed_data = json.loads(message["data"])
                    except json.decoder.JSONDecodeError:
                        log.exception("Bad JSON data on %s topic: '%s'", message["channel"], message["data"])
                        continue

                    for handler in self.handlers[message["channel"]]:
                        # invokes the handler on the bot's main thread (the IRC event loop)
                        # TODO: do we need to execute delayed somehow? xd
                        handler(parsed_data)

    async def start(self) -> None:
        async with RedisManager.get_async().pubsub() as pubsub:
            await pubsub.psubscribe(f"{self.streamer_name}:*")

            await self.reader(pubsub)


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

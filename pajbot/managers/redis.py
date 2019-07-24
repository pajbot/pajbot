import logging
import os
from contextlib import contextmanager

import redis

log = logging.getLogger(__name__)


class RedisManager:
    """
    Responsible for making sure exactly one instance of Redis
    is initialized with the right arguments, and returns when the
    get-method is called.
    """

    redis = None

    @staticmethod
    def init(**options):
        default_options = {"decode_responses": True, "host": os.environ.get("REDIS", "localhost")}
        default_options.update(options)
        RedisManager.redis = redis.Redis(**default_options)

    @staticmethod
    def get():
        return RedisManager.redis

    @staticmethod
    @contextmanager
    def pipeline_context():
        try:
            pipeline = RedisManager.get().pipeline()
            yield pipeline
        except:
            log.exception("Exception caught during RedisManager::pipeline_context")
            pipeline.reset()
        finally:
            pipeline.execute()

    @classmethod
    def publish(cls, channel, message):
        cls.redis.publish(channel, message)

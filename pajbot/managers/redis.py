from contextlib import contextmanager

import redis


class RedisManager:
    """
    Responsible for making sure exactly one instance of Redis
    is initialized with the right arguments, and returns when the
    get-method is called.
    """

    redis = None

    def init(**options):
        default_options = {
                'decode_responses': True,
                }
        default_options.update(options)
        RedisManager.redis = redis.Redis(**default_options)

    def get():
        return RedisManager.redis

    @contextmanager
    def pipeline_context():
        try:
            pipeline = RedisManager.get().pipeline()
            yield pipeline
        except:
            pipeline.reset()
        finally:
            pipeline.execute()

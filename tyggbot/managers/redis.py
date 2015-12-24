import redis

class RedisManager:
    """
    Responsible for making sure exactly one instance of Redis
    is initialized with the right arguments, and returns when the
    get-method is called.
    """

    redis = None

    def init(**options):
        RedisManager.redis = redis.Redis(**options)

    def get():
        return RedisManager.redis

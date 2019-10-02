from contextlib import contextmanager

from redis import Redis


class RedisMigratable:
    def __init__(self, redis_options, namespace):
        self.redis_options = redis_options
        self.namespace = namespace

    @contextmanager
    def create_resource(self):
        redis = None

        try:
            redis = Redis(**self.redis_options)
            yield redis
        finally:
            if redis is not None:
                redis.connection_pool.disconnect()

    def get_current_revision(self, redis):
        response = redis.get(self.namespace + ":schema-version")

        if response is None:
            return None
        else:
            return int(response)

    def set_revision(self, redis, id):
        redis.set(self.namespace + ":schema_version", id)

    @staticmethod
    def describe_resource():
        return "redis"

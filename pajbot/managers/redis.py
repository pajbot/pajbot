from __future__ import annotations

from typing import TYPE_CHECKING, ContextManager, Literal, Mapping, Optional, TypedDict, Union, Any

import logging

import redis
from redis import Redis
from redis.client import Pipeline

# from redis.connection import ConnectionPool

log = logging.getLogger(__name__)

if TYPE_CHECKING:
    _StrType = str
    RedisType = Redis[_StrType]


# class RedisOptions(TypedDict):
#     decode_responses: Literal[True]
#     host: str
#     port: int
#     db: int
#     password: Optional[str]
#     socket_timeout: Optional[float]
#     socket_connect_timeout: Optional[float]
#     socket_keepalive: Optional[bool]
#     socket_keepalive_options: Optional[Mapping[str, Union[int, str]]]
#     connection_pool: Optional[ConnectionPool]
#     unix_socket_path: Optional[str]
#     encoding: str
#     encoding_errors: str
#     charset: Optional[str]
#     errors: Optional[str]
#     retry_on_timeout: bool
#     ssl: bool
#     ssl_keyfile: Optional[str]
#     ssl_certfile: Optional[str]
#     ssl_cert_reqs: Union[str, int, None]
#     ssl_ca_certs: Optional[str]
#     ssl_check_hostname: bool
#     max_connections: Optional[int]
#     single_connection_client: bool
#     health_check_interval: float
#     client_name: Optional[str]
#     username: Optional[str]


class RedisManager:
    """
    Responsible for making sure exactly one instance of Redis
    is initialized with the right arguments, and returns when the
    get-method is called.
    """

    redis: Optional[RedisType] = None

    @staticmethod
    def init(options: dict[Any, Any]) -> None:
        if RedisManager.redis is not None:
            raise ValueError("RedisManager.init has already been called once")

        if "decode_responses" in options:
            raise ValueError("You may not change decode_responses in RedisManager.init options")

        options["decode_responses"] = True

        RedisManager.redis = Redis(**options)

    @staticmethod
    def get() -> RedisType:
        if RedisManager.redis is None:
            raise ValueError("RedisManager.get called before RedisManager.init")

        return RedisManager.redis

    @staticmethod
    def pipeline_context() -> ContextManager[Pipeline[_StrType]]:
        return redis.utils.pipeline(RedisManager.get())

    @classmethod
    def publish(cls, channel: str, message: str) -> int:
        if cls.redis is None:
            raise ValueError("RedisManager.publish called before RedisManager.init")

        return cls.redis.publish(channel, message)

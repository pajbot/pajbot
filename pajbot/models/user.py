import datetime
import json
import logging
from contextlib import contextmanager

from sqlalchemy import Boolean
from sqlalchemy import Column
from sqlalchemy import Integer
from sqlalchemy import String

from pajbot.exc import FailedCommand
from pajbot.managers.db import Base
from pajbot.managers.db import DBManager
from pajbot.managers.redis import RedisManager
from pajbot.managers.schedule import ScheduleManager
from pajbot.managers.time import TimeManager
from pajbot.streamhelper import StreamHelper
from pajbot.utils import time_method  # NOQA

log = logging.getLogger(__name__)


class User(Base):
    __tablename__ = 'tb_user'

    id = Column(Integer, primary_key=True)
    username = Column(String(32), nullable=False, index=True, unique=True)
    username_raw = Column(String(32))
    level = Column(Integer, nullable=False, default=100)
    points = Column(Integer, nullable=False, default=0, index=True)
    subscriber = Column(Boolean, nullable=False, default=False)
    minutes_in_chat_online = Column(Integer, nullable=False, default=0)
    minutes_in_chat_offline = Column(Integer, nullable=False, default=0)

    def __init__(self, username):
        self.id = None
        self.username = username.lower()
        self.username_raw = username
        self.level = 100
        self.points = 0
        self.subscriber = False
        self.minutes_in_chat_online = 0
        self.minutes_in_chat_offline = 0

        self.quest_progress = {}
        self.debts = []

        self.timed_out = False

    @classmethod
    def test_user(cls, username):
        user = cls()

        user.id = 123
        user.username = username.lower()
        user.username_raw = username
        user.level = 2000
        user.subscriber = True
        user.points = 1234
        user.minutes_in_chat_online = 5
        user.minutes_in_chat_offline = 15

        return user


class NoCacheHit(Exception):
    pass


class UserSQLCache:
    cache = {}

    def init():
        ScheduleManager.execute_every(30 * 60, UserSQLCache._clear_cache)

    def _clear_cache():
        UserSQLCache.cache = {}

    def save(user):
        UserSQLCache.cache[user.username] = {
                'id': user.id,
                'level': user.level,
                'subscriber': user.subscriber,
                }

    def get(username, value):
        if username not in UserSQLCache.cache:
            raise NoCacheHit('User not in cache')

        if value not in UserSQLCache.cache[username]:
            raise NoCacheHit('Value not in cache')

        # log.debug('Returning {}:{} from cache'.format(username, value))
        return UserSQLCache.cache[username][value]


class UserSQL:
    def __init__(self, username, db_session, user_model=None):
        self.username = username
        self.user_model = user_model
        self.model_loaded = user_model is not None
        self.shared_db_session = db_session

    def select_or_create(db_session, username):
        user = db_session.query(User).filter_by(username=username).one_or_none()
        if user is None:
            user = User(username)
            db_session.add(user)
        return user

    # @time_method
    def sql_load(self):
        if self.model_loaded:
            return

        self.model_loaded = True

        # log.debug('[UserSQL] Loading user model for {}'.format(self.username))
        # from pajbot.utils import print_traceback
        # print_traceback()

        if self.shared_db_session:
            user = UserSQL.select_or_create(self.shared_db_session, self.username)
        else:
            with DBManager.create_session_scope(expire_on_commit=False) as db_session:
                user = UserSQL.select_or_create(db_session, self.username)
                db_session.expunge(user)

        self.user_model = user

    def sql_save(self, save_to_db=True):
        if not self.model_loaded:
            return

        try:
            if save_to_db and not self.shared_db_session:
                with DBManager.create_session_scope(expire_on_commit=False) as db_session:
                    # log.debug('Calling db_session.add on {}'.format(self.user_model))
                    db_session.add(self.user_model)

            UserSQLCache.save(self.user_model)
        except:
            log.exception('Caught exception in sql_save while saving {}'.format(self.user_model))

    @property
    def id(self):
        try:
            return UserSQLCache.get(self.username, 'id')
        except NoCacheHit:
            self.sql_load()
            return self.user_model.id

    @id.setter
    def id(self, value):
        self.sql_load()
        self.user_model.id = value

    @property
    def level(self):
        try:
            return UserSQLCache.get(self.username, 'level')
        except NoCacheHit:
            self.sql_load()
            return self.user_model.level

    @level.setter
    def level(self, value):
        self.sql_load()
        self.user_model.level = value

    @property
    def minutes_in_chat_online(self):
        try:
            return UserSQLCache.get(self.username, 'minutes_in_chat_online')
        except NoCacheHit:
            self.sql_load()
            return self.user_model.minutes_in_chat_online

    @minutes_in_chat_online.setter
    def minutes_in_chat_online(self, value):
        self.sql_load()
        self.user_model.minutes_in_chat_online = value

    @property
    def minutes_in_chat_offline(self):
        try:
            return UserSQLCache.get(self.username, 'minutes_in_chat_offline')
        except NoCacheHit:
            self.sql_load()
            return self.user_model.minutes_in_chat_offline

    @minutes_in_chat_offline.setter
    def minutes_in_chat_offline(self, value):
        self.sql_load()
        self.user_model.minutes_in_chat_offline = value

    @property
    def subscriber(self):
        try:
            return UserSQLCache.get(self.username, 'subscriber')
        except NoCacheHit:
            self.sql_load()
            return self.user_model.subscriber

    @subscriber.setter
    def subscriber(self, value):
        try:
            old_value = UserSQLCache.get(self.username, 'subscriber')
            if old_value == value:
                return
        except NoCacheHit:
            pass

        self.sql_load()
        self.user_model.subscriber = value

    @property
    def points(self):
        self.sql_load()
        return self.user_model.points

    @points.setter
    def points(self, value):
        self.sql_load()
        self.user_model.points = value

    @property
    def points_rank(self):
        return 420
        """
        if self.shared_db_session:
            query_data = self.shared_db_session.query(sqlalchemy.func.count(User.id)).filter(User.points > self.points).one()
        else:
            with DBManager.create_session_scope(expire_on_commit=False) as db_session:
                query_data = db_session.query(sqlalchemy.func.count(User.id)).filter(User.points > self.points).one()

        rank = int(query_data[0]) + 1
        return rank
        """

    @property
    def duel_stats(self):
        self.sql_load()
        return self.user_model.duel_stats

    @duel_stats.setter
    def duel_stats(self, value):
        self.sql_load()
        self.user_model.duel_stats = value


class UserRedis:
    SS_KEYS = [
            'num_lines',
            'tokens',
            ]
    HASH_KEYS = [
            'last_seen',
            'last_active',
            'username_raw',
            ]
    BOOL_KEYS = [
            'ignored',
            'banned',
            ]
    FULL_KEYS = SS_KEYS + HASH_KEYS + BOOL_KEYS

    SS_DEFAULTS = {
            'num_lines': 0,
            'tokens': 0,
            }
    HASH_DEFAULTS = {
            'last_seen': None,
            'last_active': None,
            }

    def __init__(self, username, redis=None):
        self.username = username
        self.redis_loaded = False
        self.save_to_redis = True
        self.values = {}
        if redis:
            self.redis = redis
        else:
            self.redis = RedisManager.get()

    def queue_up_redis_calls(self, pipeline):
        streamer = StreamHelper.get_streamer()
        # Queue up calls to the pipeline
        for key in UserRedis.SS_KEYS:
            pipeline.zscore('{streamer}:users:{key}'.format(streamer=streamer, key=key), self.username)
        for key in UserRedis.HASH_KEYS:
            pipeline.hget('{streamer}:users:{key}'.format(streamer=streamer, key=key), self.username)
        for key in UserRedis.BOOL_KEYS:
            pipeline.hget('{streamer}:users:{key}'.format(streamer=streamer, key=key), self.username)

    def load_redis_data(self, data):
        self.redis_loaded = True
        full_keys = list(UserRedis.FULL_KEYS)
        for value in data:
            key = full_keys.pop(0)
            if key in UserRedis.SS_KEYS:
                self.values[key] = self.fix_ss(key, value)
            elif key in UserRedis.HASH_KEYS:
                self.values[key] = self.fix_hash(key, value)
            else:
                self.values[key] = self.fix_bool(key, value)

    # @time_method
    def redis_load(self):
        """ Load data from redis using a newly created pipeline """
        if self.redis_loaded:
            return

        with RedisManager.pipeline_context() as pipeline:
            self.queue_up_redis_calls(pipeline)
            data = pipeline.execute()
            self.load_redis_data(data)

    def fix_ss(self, key, value):
        try:
            val = int(value)
        except:
            val = UserRedis.SS_DEFAULTS[key]
        return val

    def fix_hash(self, key, value):
        if key == 'username_raw':
            val = value or self.username
        else:
            val = value or UserRedis.HASH_DEFAULTS[key]

        return val

    def fix_bool(self, key, value):
        return False if value is None else True

    @property
    def new(self):
        return self._last_seen is None

    @property
    def num_lines(self):
        if self.save_to_redis:
            self.redis_load()
            return self.values['num_lines']
        else:
            return self.values.get('num_lines', 0)

    @num_lines.setter
    def num_lines(self, value):
        # Set cached value
        self.values['num_lines'] = value

        if self.save_to_redis:
            # Set redis value
            if value != 0:
                self.redis.zadd('{streamer}:users:num_lines'.format(streamer=StreamHelper.get_streamer()), self.username, value)
            else:
                self.redis.zrem('{streamer}:users:num_lines'.format(streamer=StreamHelper.get_streamer()), self.username)

    @property
    def tokens(self):
        if self.save_to_redis:
            self.redis_load()
            return self.values['tokens']
        else:
            return self.values.get('tokens', 0)

    @tokens.setter
    def tokens(self, value):
        # Set cached value
        self.values['tokens'] = value

        if self.save_to_redis:
            # Set redis value
            if value != 0:
                self.redis.zadd('{streamer}:users:tokens'.format(streamer=StreamHelper.get_streamer()), self.username, value)
            else:
                self.redis.zrem('{streamer}:users:tokens'.format(streamer=StreamHelper.get_streamer()), self.username)

    @property
    def num_lines_rank(self):
        key = '{streamer}:users:num_lines'.format(streamer=StreamHelper.get_streamer())
        rank = self.redis.zrevrank(key, self.username)
        if rank is None:
            return self.redis.zcard(key)
        else:
            return rank + 1

    @property
    def _last_seen(self):
        self.redis_load()
        try:
            return datetime.datetime.utcfromtimestamp(float(self.values['last_seen']))
        except:
            return None

    @_last_seen.setter
    def _last_seen(self, value):
        # Set cached value
        value = value.timestamp()
        self.values['last_seen'] = value

        # Set redis value
        self.redis.hset('{streamer}:users:last_seen'.format(streamer=StreamHelper.get_streamer()), self.username, value)

    def set_last_seen(self, value):
        # Set cached value
        value = value.timestamp()
        self.values['last_seen'] = value

        # Set redis value
        self.redis.hset('{streamer}:users:last_seen'.format(streamer=StreamHelper.get_streamer()), self.username, value)

    def _set_last_seen(self, value):
        # Set cached value
        self.values['last_seen'] = value

        self.redis.hset('{streamer}:users:last_seen'.format(streamer=StreamHelper.get_streamer()), self.username, value)

    @property
    def _last_active(self):
        self.redis_load()
        try:
            return datetime.datetime.utcfromtimestamp(float(self.values['last_active']))
        except:
            return None

    @_last_active.setter
    def _last_active(self, value):
        # Set cached value
        value = value.timestamp()
        self.values['last_active'] = value

        # Set redis value
        self.redis.hset('{streamer}:users:last_active'.format(streamer=StreamHelper.get_streamer()), self.username, value)

    @property
    def username_raw(self):
        self.redis_load()
        return self.values['username_raw']

    @username_raw.setter
    def username_raw(self, value):
        # Set cached value
        self.values['username_raw'] = value

        # Set redis value
        if value != self.username:
            self.redis.hset('{streamer}:users:username_raw'.format(streamer=StreamHelper.get_streamer()), self.username, value)
        else:
            self.redis.hdel('{streamer}:users:username_raw'.format(streamer=StreamHelper.get_streamer()), self.username)

    @property
    def ignored(self):
        self.redis_load()
        return self.values['ignored']

    @ignored.setter
    def ignored(self, value):
        # Set cached value
        self.values['ignored'] = value

        if value is True:
            # Set redis value
            self.redis.hset('{streamer}:users:ignored'.format(streamer=StreamHelper.get_streamer()), self.username, 1)
        else:
            self.redis.hdel('{streamer}:users:ignored'.format(streamer=StreamHelper.get_streamer()), self.username)

    @property
    def banned(self):
        self.redis_load()
        return self.values['banned']

    @banned.setter
    def banned(self, value):
        # Set cached value
        self.values['banned'] = value

        if value is True:
            # Set redis value
            self.redis.hset('{streamer}:users:banned'.format(streamer=StreamHelper.get_streamer()), self.username, 1)
        else:
            self.redis.hdel('{streamer}:users:banned'.format(streamer=StreamHelper.get_streamer()), self.username)


class UserCombined(UserRedis, UserSQL):
    """
    A combination of the MySQL Object and the Redis object
    """

    WARNING_SYNTAX = '{prefix}_{username}_warning_{id}'

    def __init__(self, username, db_session=None, user_model=None, redis=None):
        UserSQL.__init__(self, username, db_session, user_model=user_model)
        UserRedis.__init__(self, username, redis=redis)

        self.debts = []
        self.moderator = False
        self.timed_out = False
        self.timeout_end = None

    def load(self, **attrs):
        vars(self).update(attrs)

    def save(self, save_to_db=True):
        self.sql_save(save_to_db=save_to_db)
        return {
                'debts': self.debts,
                'moderator': self.moderator,
                'timed_out': self.timed_out,
                'timeout_end': self.timeout_end,
                }

    def jsonify(self):
        return {
                'id': self.id,
                'username': self.username,
                'username_raw': self.username_raw,
                'points': self.points,
                'nl_rank': self.num_lines_rank,
                'points_rank': self.points_rank,
                'level': self.level,
                'last_seen': self.last_seen,
                'last_active': self.last_active,
                'subscriber': self.subscriber,
                'num_lines': self.num_lines,
                'minutes_in_chat_online': self.minutes_in_chat_online,
                'minutes_in_chat_offline': self.minutes_in_chat_offline,
                'banned': self.banned,
                'ignored': self.ignored,
                }

    def get_tags(self, redis=None):
        if redis is None:
            redis = RedisManager.get()
        val = redis.hget('global:usertags', self.username)
        if val:
            return json.loads(val)
        else:
            return {}

    @property
    def last_seen(self):
        ret = TimeManager.localize(self._last_seen)
        return ret

    @last_seen.setter
    def last_seen(self, value):
        self.set_last_seen(value)

    @property
    def last_active(self):
        if self._last_active is None:
            return None
        return TimeManager.localize(self._last_active)

    @last_active.setter
    def last_active(self, value):
        self._last_active = value

    def set_tags(self, value, redis=None):
        if redis is None:
            redis = RedisManager.get()
        return redis.hset('global:usertags', self.username, json.dumps(value, separators=(',', ':')))

    def create_debt(self, points):
        self.debts.append(points)

    def get_warning_keys(self, total_chances, prefix):
        """ Returns a list of keys that are used to store the users warning status in redis.
        Example: ['pajlada_warning1', 'pajlada_warning2'] """
        return [self.WARNING_SYNTAX.format(prefix=prefix, username=self.username, id=id) for id in range(0, total_chances)]

    def get_warnings(self, redis, warning_keys):
        """ Pass through a list of warning keys.
        Example of warning_keys syntax: ['_pajlada_warning1', '_pajlada_warning2']
        Returns a list of values for the warning keys list above.
        Example: [b'1', None]
        Each instance of None in the list means one more Chance
        before a full timeout is in order. """

        return redis.mget(warning_keys)

    def get_chances_used(self, warnings):
        """ Returns a number between 0 and n where n is the amount of
            chances a user has before he should face the full timeout length. """

        return len(warnings) - warnings.count(None)

    def add_warning(self, redis, timeout, warning_keys, warnings):
        """ Returns a number between 0 and n where n is the amount of
            chances a user has before he should face the full timeout length. """

        for id in range(0, len(warning_keys)):
            if warnings[id] is None:
                redis.setex(warning_keys[id], time=timeout, value=1)
                return True

        return False

    def timeout(self, timeout_length, warning_module=None, use_warnings=True):
        """ Returns a tuple with the follow data:
        How long to timeout the user for, and what the punishment string is
        set to.
        The punishment string is used to clarify whether this was a warning or the real deal.
        """

        punishment = 'timed out for {} seconds'.format(timeout_length)

        if use_warnings and warning_module is not None:
            redis = RedisManager.get()

            """ How many chances the user has before receiving a full timeout. """
            total_chances = warning_module.settings['total_chances']

            warning_keys = self.get_warning_keys(total_chances, warning_module.settings['redis_prefix'])
            warnings = self.get_warnings(redis, warning_keys)

            chances_used = self.get_chances_used(warnings)

            if chances_used < total_chances:
                """ The user used up one of his warnings.
                Calculate for how long we should time him out. """
                timeout_length = warning_module.settings['base_timeout'] * (chances_used + 1)
                punishment = 'timed out for {} seconds (warning)'.format(timeout_length)

                self.add_warning(redis, warning_module.settings['length'], warning_keys, warnings)

        return (timeout_length, punishment)

    @contextmanager
    def spend_currency_context(self, points_to_spend, tokens_to_spend):
        # TODO: After the token storage rewrite, use tokens here too
        try:
            self._spend_points(points_to_spend)
            self._spend_tokens(tokens_to_spend)
            yield
        except FailedCommand:
            log.debug('Returning {} points to {}'.format(points_to_spend, self.username_raw))
            self.points += points_to_spend
            self.tokens += tokens_to_spend
        except:
            # An error occured, return the users points!
            log.exception('XXXX')
            log.debug('Returning {} points to {}'.format(points_to_spend, self.username_raw))
            self.points += points_to_spend

    def _spend_points(self, points_to_spend):
        """ Returns true if points were spent, otherwise return False """
        if points_to_spend <= self.points:
            self.points -= points_to_spend
            return True

        return False

    def _spend_tokens(self, tokens_to_spend):
        """ Returns true if tokens were spent, otherwise return False """
        if tokens_to_spend <= self.tokens:
            self.tokens -= tokens_to_spend
            return True

        return False

    def remove_debt(self, debt):
        try:
            self.debts.remove(debt)
        except ValueError:
            log.error('For some reason the debt {} was not in the list of debts {}'.format(debt, self.debts))

    def pay_debt(self, debt):
        self.points -= debt
        self.remove_debt(debt)

    def points_in_debt(self):
        return sum(self.debts)

    def points_available(self):
        return self.points - self.points_in_debt()

    def can_afford(self, points_to_spend):
        return self.points_available() >= points_to_spend

    def __eq__(self, other):
        return self.username == other.username

    def can_afford_with_tokens(self, cost):
        return self.tokens >= cost

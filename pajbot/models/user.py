import datetime
import json
import logging
from collections import UserDict
from contextlib import contextmanager

from sqlalchemy import Boolean
from sqlalchemy import Column
from sqlalchemy import DateTime
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy.orm import reconstructor

from pajbot.managers import Base
from pajbot.managers import DBManager
from pajbot.managers import HandlerManager
from pajbot.managers import RedisManager
from pajbot.managers import TimeManager
from pajbot.streamhelper import StreamHelper

log = logging.getLogger('pajbot')


class User(Base):
    __tablename__ = 'tb_user'

    id = Column(Integer, primary_key=True)
    username = Column(String(128), nullable=False, index=True, unique=True)
    username_raw = Column(String(128))
    level = Column(Integer, nullable=False, default=100)
    points = Column(Integer, nullable=False, default=0)
    num_lines = Column(Integer, nullable=False, default=0)
    subscriber = Column(Boolean, nullable=False, default=False)
    _last_seen = Column('last_seen', DateTime)
    _last_active = Column('last_active', DateTime)
    minutes_in_chat_online = Column(Integer, nullable=False, default=0)
    minutes_in_chat_offline = Column(Integer, nullable=False, default=0)
    ignored = Column(Boolean, nullable=False, default=False)
    banned = Column(Boolean, nullable=False, default=False)
    ban_immune = False
    moderator = False

    WARNING_SYNTAX = '{prefix}_{username}_warning_{id}'

    def __init__(self, username):
        self.id = None
        self.username = username.lower()
        self.username_raw = username
        self.level = 100
        self.points = 0
        self.num_lines = 0
        self.subscriber = False
        self._last_seen = datetime.datetime.now()
        self._last_active = None
        self.minutes_in_chat_online = 0
        self.minutes_in_chat_offline = 0
        self.ignored = False
        self.banned = False
        self.moderator = False

        self.ban_immune = False
        self.quest_progress = {}
        self.debts = []

        self.timed_out = False

    def get_tags(self, redis=None):
        if redis is None:
            redis = RedisManager.get()
        val = redis.hget('global:usertags', self.username)
        if val:
            return json.loads(val)
        else:
            return {}

    def set_tags(self, value, redis=None):
        if redis is None:
            redis = RedisManager.get()
        return redis.hset('global:usertags', self.username, json.dumps(value, separators=(',', ':')))

    @property
    def last_seen(self):
        return TimeManager.localize(self._last_seen)

    @last_seen.setter
    def last_seen(self, value):
        self._last_seen = value

    @property
    def last_active(self):
        if self._last_active is None:
            return None
        return TimeManager.localize(self._last_active)

    @last_active.setter
    def last_active(self, value):
        self._last_active = value

    @reconstructor
    def on_load(self):
        self.timed_out = False
        self.moderator = False
        self.quest_progress = {}
        self.debts = []

    def can_afford_with_tokens(self, cost):
        num_tokens = self.get_tokens()
        return num_tokens >= cost

    def spend_tokens(self, tokens_to_spend, redis=None):
        if redis is None:
            redis = RedisManager.get()

        user_token_key = '{streamer}:{username}:tokens'.format(
                streamer=StreamHelper.get_streamer(), username=self.username)

        token_dict = redis.hgetall(user_token_key)

        for stream_id in token_dict:
            try:
                num_tokens = int(token_dict[stream_id])
            except (TypeError, ValueError):
                continue

            if num_tokens == 0:
                continue

            decrease_by = min(tokens_to_spend, num_tokens)
            tokens_to_spend -= decrease_by
            num_tokens -= decrease_by

            redis.hset(user_token_key, stream_id, num_tokens)

            if tokens_to_spend == 0:
                return True

        return False

    def award_tokens(self, tokens, redis=None, force=False):
        """ Returns True if tokens were awarded properly.
        Returns False if not.
        Tokens can only be rewarded once per stream ID.
        """

        streamer = StreamHelper.get_streamer()
        stream_id = StreamHelper.get_current_stream_id()

        if stream_id is False:
            return False

        if redis is None:
            redis = RedisManager.get()

        key = '{streamer}:{username}:tokens'.format(
                streamer=streamer, username=self.username)

        if force:
            res = True
            redis.hset(key, stream_id, tokens)
        else:
            res = True if redis.hsetnx(key, stream_id, tokens) == 1 else False
            if res is True:
                HandlerManager.trigger('on_user_gain_tokens', self, tokens)
        return res

    def get_tokens(self, redis=None):
        streamer = StreamHelper.get_streamer()
        if redis is None:
            redis = RedisManager.get()

        tokens = redis.hgetall('{streamer}:{username}:tokens'.format(
            streamer=streamer, username=self.username))

        num_tokens = 0
        for token_value in tokens.values():
            try:
                num_tokens += int(token_value)
            except (TypeError, ValueError):
                log.warn('Invalid value for tokens, user {}'.format(self.username))

        return num_tokens

    def remove_ban_immunity(self):
        self.ban_immune = False

    """
    Update the capitalization of a users username.
    """
    def update_username(self, new_username):
        if self.username_raw != new_username:
            # The capitalization has changed!
            self.username_raw = new_username

    def __eq__(self, other):
        return self.username == other.username

    @classmethod
    def test_user(cls, username):
        user = cls()

        user.id = 123
        user.username = username.lower()
        user.username_raw = username
        user.level = 2000
        user.num_lines = 0
        user.subscriber = True
        user.points = 1234
        user.last_seen = None
        user.last_active = None
        user.minutes_in_chat_online = 5
        user.minutes_in_chat_offline = 15

        return user

    def create_debt(self, points):
        self.debts.append(points)

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

    @contextmanager
    def spend_currency_context(self, points_to_spend, tokens_to_spend):
        # TODO: After the token storage rewrite, use tokens here too
        try:
            self.spend_points(points_to_spend)
            yield
        except:
            # An error occured, return the users points!
            log.debug('Returning {} points to {}'.format(points_to_spend, self.username_raw))
            self.points += points_to_spend

    def spend(self, points_to_spend):
        # XXX: Remove all usages of spend() and use spend_points() instead
        return self.spend_points(points_to_spend)

    def spend_points(self, points_to_spend):
        if points_to_spend <= self.points:
            self.points -= points_to_spend
            return True

        return False

    def touch(self, add_points=0):
        self.last_seen = datetime.datetime.now()
        self.points += add_points

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


class UserManager(UserDict):
    def __init__(self):
        UserDict.__init__(self)
        self.db_session = DBManager.create_session()

    @classmethod
    def init_for_tests(cls):
        users = cls(None)

        users['pajlada'] = User.test_user('PajladA')

        return users

    def commit(self):
        self.db_session.commit()

    def find(self, username):
        """
        Attempts to find the user with the given username.

        Arguments:
        username - Username of the user we're trying to find. Case-insensitive.

        Returns a user object if the user already existed, otherwise return None
        """

        # from pajbot.tbutil import print_traceback
        # print_traceback()

        # log.debug('UserManager::find({})'.format(username))

        # Return None if the username is an empty string!
        if username == '':
            return None

        # This will be used when we access the cache dictionary
        username_lower = username.lower()

        # Replace any occurances of @ in the username
        # This helps non-bttv-users who tab-complete usernames
        username = username.replace('@', '')

        # Check if the user is already cached
        if username_lower in self.data:
            return self.data[username_lower]

        # Check for the username in the database
        user = self.db_session.query(User).filter_by(username=username_lower).one_or_none()

        return user

    def bulk_load(self, usernames):
        """ Takes a list of usernames, and returns a list of User objects """

        # First we make sure the list is unique
        usernames = set(usernames)
        users = []
        for user in self.db_session.query(User).filter(User.username.in_(usernames)):
            try:
                usernames.remove(user.username)
            except:
                log.exception('Exception caught while removing {0} from the usernames list'.format(user.username))
            self.data[user.username] = user
            users.append(user)

        for username in usernames:
            # New user!
            user = User(username=username)
            self.db_session.add(user)
            self.data[username] = user
            users.append(user)
        self.db_session.flush()

        return users

    def __getitem__(self, username):
        """
        Returns the user with the given username.
        If the user does not exist, create it.

        Arguments:
        username - Username of the user we're trying to find/create. Case-insensitive.

        Returns a user object for the given username.
        """

        # log.debug('UserManager::__getitem__({})'.format(username))

        # This will be used when we access the cache dictionary
        username_lower = username.lower()

        # Check if the user is already cached
        if username_lower in self.data:
            return self.data[username_lower]

        # Check for the username in the database
        user = self.db_session.query(User).filter_by(username=username_lower).one_or_none()

        # If the user did not exist, create it
        if user is None:
            user = User(username=username)
            self.db_session.add(user)
            self.db_session.flush()

        # Add the user object to the cache
        self.data[username_lower] = user

        return self.data[username_lower]

    def reset_subs(self):
        for user in self.db_session.query(User).filter_by(subscriber=True):
            if user.username not in self.data:
                self.data[user.username] = user

            user.subscriber = False

    """ Load all users WutFace
    def reload(self):
        self.data = {}
        num_users = 0
        for user in self.db_session.query(User):
            num_users += 1
            self.data[user.username] = user

        log.info('Loaded {0} users'.format(num_users))
        return self
        """

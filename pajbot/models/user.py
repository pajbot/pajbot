import logging
from collections import UserDict
import datetime

from pajbot.models.db import DBManager, Base
from pajbot.models.time import TimeManager
from pajbot.managers import RedisManager

from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy import orm

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
    twitch_access_token = Column(String(128), nullable=True)
    twitch_refresh_token = Column(String(128), nullable=True)
    discord_user_id = Column(String(32), nullable=True)
    ignored = Column(Boolean, nullable=False, default=False)
    banned = Column(Boolean, nullable=False, default=False)
    ban_immune = False
    moderator = False

    WARNING_SYNTAX = '{prefix}_{username}_warning_{id}'

    def __init__(self, username):
        self.id = None
        self.username = username
        self.username_raw = username
        self.level = 100
        self.points = 0
        self.num_lines = 0
        self.subscriber = False
        self._last_seen = datetime.datetime.now()
        self._last_active = None
        self.minutes_in_chat_online = 0
        self.minutes_in_chat_offline = 0
        self.twitch_access_token = None
        self.twitch_refresh_token = None
        self.discord_user_id = None
        self.ignored = False
        self.banned = False
        self.moderator = False

        self.ban_immune = False
        self.tags = []

        self.timed_out = False

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

    @orm.reconstructor
    def on_load(self):
        self.tags = []
        self.timed_out = False
        self.moderator = False

    def tag_as(self, tag):
        if tag not in self.tags:
            log.debug('{0} has been tagged as a {1}'.format(self.username, tag))
            self.tags.append(tag)
            return True

        return False

    def remove_tag(self, tag):
        try:
            self.tags.remove(tag)
            log.debug('{0} has been un-tagged as a {1}'.format(self.username, tag))
        except ValueError:
            pass

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

    def spend(self, points_to_spend):
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
        if username in self.data:
            return self.data[username]

        user = self[username]
        if user.id is None:
            self.db_session.expunge(user)
            del self.data[username]
            return None
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

        return users

    def __getitem__(self, key):
        if key not in self.data:
            user = self.db_session.query(User).filter_by(username=key.lower()).one_or_none()
            if user is None:
                user = User(username=key)
                self.db_session.add(user)

            self.data[key] = user

        return self.data[key]

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

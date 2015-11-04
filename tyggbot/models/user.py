import logging
from collections import UserDict
import datetime

from tyggbot.models.db import DBManager, Base

from sqlalchemy import Column, Integer, String, Boolean, DateTime

log = logging.getLogger('tyggbot')


class User(Base):
    __tablename__ = 'tb_user'

    id = Column(Integer, primary_key=True)
    username = Column(String(128))
    username_raw = Column(String(128))
    level = Column(Integer)
    points = Column(Integer)
    num_lines = Column(Integer)
    subscriber = Column(Boolean)
    last_seen = Column(DateTime)
    last_active = Column(DateTime)
    minutes_in_chat_online = Column(Integer)
    minutes_in_chat_offline = Column(Integer)
    twitch_access_token = Column(String(128))
    twitch_refresh_token = Column(String(128))
    discord_user_id = Column(String(32))
    ignored = Column(Boolean)
    banned = Column(Boolean)
    ban_immune = False

    def __init__(self, username):
        self.id = None
        self.username = username
        self.username_raw = username
        self.level = 100
        self.points = 0
        self.num_lines = 0
        self.subscriber = False
        self.last_seen = datetime.datetime.now()
        self.last_active = None
        self.minutes_in_chat_online = 0
        self.minutes_in_chat_offline = 0
        self.twitch_access_token = None
        self.twitch_refresh_token = None
        self.discord_user_id = None
        self.ignored = False
        self.banned = False

        self.ban_immune = False

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

    def wrote_message(self, add_line=True):
        self.last_active = datetime.datetime.now()
        self.last_seen = datetime.datetime.now()
        if add_line:
            self.num_lines += 1


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
        for user in self.db_session.query(User).filter(User.username.in_(usernames)):
            usernames.remove(user.username)
            self.data[user.username] = user

        for username in usernames:
            log.info('{0} is a new user.'.format(username))
            # New user!
            user = User(username=username)
            self.db_session.add(user)
            self.data[username] = user

    def __getitem__(self, key):
        if key not in self.data:
            user = self.db_session.query(User).filter_by(username=key.lower()).one_or_none()
            if user is None:
                user = User(username=key)
                self.db_session.add(user)

            self.data[key] = user

        return self.data[key]

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

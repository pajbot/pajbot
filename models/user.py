import logging
from collections import UserDict
import pymysql
import datetime
from tbutil import create_insert_query, create_update_query

log = logging.getLogger('tyggbot')


class User:
    def __init__(self):
        self.needs_sync = False
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
            self.needs_sync = True

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

    @classmethod
    def load(cls, cursor, username):
        user = cls()

        cursor.execute('SELECT * FROM `tb_user` WHERE `username`=%s', (username.lower()))
        row = cursor.fetchone()
        if row:
            # We found a user in the database!
            user.id = row['id']
            user.username = row['username']
            user.username_raw = row['username_raw']
            user.level = row['level']
            user.num_lines = row['num_lines']
            user.subscriber = row['subscriber'] == 1
            user.points = row['points']
            user.last_seen = row['last_seen']
            user.last_active = row['last_active']
            user.minutes_in_chat_online = row['minutes_in_chat_online']
            user.minutes_in_chat_offline = row['minutes_in_chat_offline']
            user.discord_user_id = row['discord_user_id']
            user.ignored = int(row['ignored']) == 1
            user.banned = int(row['banned']) == 1
        else:
            # No user was found with this username, create a new one!
            user.id = -1  # An ID of -1 means it will be inserted on sync
            user.username = username.lower()
            user.username_raw = user.username
            user.level = 100
            user.num_lines = 0
            user.subscriber = False
            user.points = 0
            user.last_seen = None
            user.last_active = None
            user.minutes_in_chat_online = 0
            user.minutes_in_chat_offline = 0
            user.discord_user_id = None
            user.banned = False
            user.ignored = False

        return user

    def spend(self, points_to_spend):
        if points_to_spend <= self.points:
            self.points -= points_to_spend
            self.needs_sync = True
            return True

        return False

    def sync(self, cursor):
        _last_seen = None if not self.last_seen else self.last_seen.strftime('%Y-%m-%d %H:%M:%S')
        _last_active = None if not self.last_active else self.last_active.strftime('%Y-%m-%d %H:%M:%S')
        values_to_update = {
                'level': self.level,
                'num_lines': self.num_lines,
                'subscriber': self.subscriber,
                'points': self.points,
                'last_seen': _last_seen,
                'last_active': _last_active,
                'minutes_in_chat_online': self.minutes_in_chat_online,
                'minutes_in_chat_offline': self.minutes_in_chat_offline,
                'username_raw': self.username_raw,
                'discord_user_id': self.discord_user_id,
                'ignored': self.ignored,
                'banned': self.banned,
                }
        if self.id == -1:
            # Values that should be inserted, but not updated.
            values_to_insert = {
                    'username': self.username,
                    }
            values_to_insert.update(values_to_update)

            # TODO: Cache the query
            query = create_insert_query('tb_user', values_to_insert)
            values = [value for key, value in values_to_insert.items()]
            cursor.execute(query, values)
            self.id = cursor.lastrowid
        else:
            # TODO: Cache the query
            query = create_update_query('tb_user', values_to_update, 'WHERE `id`={0}'.format(self.id))
            values = [value for key, value in values_to_update.items()]
            cursor.execute(query, values)
        self.needs_sync = False

    def touch(self, add_points=0):
        self.last_seen = datetime.datetime.now()
        self.points += add_points
        self.needs_sync = True

    def wrote_message(self, add_line=True):
        self.last_active = datetime.datetime.now()
        self.last_seen = datetime.datetime.now()
        if add_line:
            self.num_lines += 1
        self.needs_sync = True


class UserManager(UserDict):
    def __init__(self, sqlconn):
        UserDict.__init__(self)
        self.sqlconn = sqlconn

    @classmethod
    def init_for_tests(cls):
        users = cls(None)

        users['pajlada'] = User.test_user('PajladA')

        return users

    def get_cursor(self):
        self.sqlconn.ping()
        return self.sqlconn.cursor(pymysql.cursors.DictCursor)

    def get_normal_cursor(self):
        self.sqlconn.ping()
        return self.sqlconn.cursor()

    def sync(self):
        self.sqlconn.autocommit(False)
        cursor = self.get_normal_cursor()
        for user in [user for k, user in self.data.items() if user.needs_sync]:
            user.sync(cursor)

        cursor.close()
        self.sqlconn.autocommit(True)

    def find(self, username):
        user = self[username]
        if user.id == -1 and user.needs_sync is False:
            del self[username]
            return None
        return user

    def __getitem__(self, key):
        if key not in self.data:
            self.data[key] = User.load(self.get_cursor(), key)

        return self.data[key]

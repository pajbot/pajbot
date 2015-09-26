import logging
from collections import UserDict
import pymysql
import datetime

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
        if self.id == -1:
            cursor.execute('INSERT INTO `tb_user` (`username`, `username_raw`, `level`, `num_lines`, `subscriber`, `points`, `last_seen`, `last_active`, `minutes_in_chat_online`, `minutes_in_chat_offline`) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)',
                    (self.username, self.username_raw, self.level, self.num_lines, self.subscriber, self.points, _last_seen, _last_active, self.minutes_in_chat_online, self.minutes_in_chat_offline))
            self.id = cursor.lastrowid
        else:
            # TODO: What values should we sync? For now, we only sync level and num_lines
            cursor.execute('UPDATE `tb_user` SET `level`=%s, `num_lines`=%s, `subscriber`=%s, `points`=%s, `last_seen`=%s, `last_active`=%s, `minutes_in_chat_online`=%s, `minutes_in_chat_offline`=%s, `username_raw`=%s WHERE `id`=%s',
                    (self.level, self.num_lines, self.subscriber, self.points, _last_seen, _last_active, self.minutes_in_chat_online, self.minutes_in_chat_offline, self.username_raw, self.id))
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

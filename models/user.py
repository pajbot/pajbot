import logging
from collections import UserDict
import pymysql

log = logging.getLogger('tyggbot')

class User:
    def __init__(self):
        self.needs_sync = False

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
        else:
            # We found a user in the database!
            user.id = -1 # An ID of -1 means it will be inserted on sync
            user.username = username.lower()
            user.username_raw = user.username
            user.level = 100
            user.num_lines = 0
            user.needs_sync = True

        return user

    def sync(self, cursor):
        if self.id == -1:
            cursor.execute('INSERT INTO `tb_user` (`username`, `username_raw`, `level`, `num_lines`) VALUES (%s, %s, %s, %s)',
                    (self.username, self.username_raw, self.level, self.num_lines))
            log.info('Inserted a new user with id {0}'.format(cursor.lastrowid))
            self.id = cursor.lastrowid
        else:
            log.debug('Syncing {0} with UPDATE'.format(self.username))
            # TODO: What values should we sync? For now, we only sync level and num_lines
            cursor.execute('UPDATE `tb_user` SET `level`=%s, `num_lines`=%s WHERE `id`=%s',
                    (self.level, self.num_lines, self.id))
        self.needs_sync = False

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
        if user.id == -1:
            del self[username]
            return None
        return user

    def __getitem__(self, key):
        if key not in self.data:
            self.data[key] = User.load(self.get_cursor(), key)

        return self.data[key]

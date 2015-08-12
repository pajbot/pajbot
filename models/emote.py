import logging
from collections import UserDict, deque
import pymysql
import re
import json

log = logging.getLogger('tyggbot')


class Emote:
    def __init__(self):
        self.id = -1  # An ID of -1 means the emote will be inserted on sync
        self.code = None  # This value will be inserted when the update_emotes script is called, if necessary.
        self.pm = 0
        self.tm = 0
        self.pm_record = 0
        self.tm_record = 0
        self.count = 0
        self.needs_sync = False
        self.regex = None

    @classmethod
    def load(cls, cursor, emote_id):
        emote = cls()

        emote.emote_id = emote_id
        emote.regex = None
        emote.needs_sync = True
        emote.deque = deque([0] * 61)

        return emote

    @classmethod
    def load_from_row(cls, row):
        emote = cls()
        emote.id = row['id']
        emote.emote_id = row['emote_id']
        emote.code = row['code']
        if not emote.emote_id:
            emote.regex = re.compile('(?<![^ ]){0}(?![^ ])'.format(re.escape(emote.code)))
        if row['deque']:
            emote.deque = deque(json.loads(row['deque']))
        else:
            emote.deque = deque([0] * 61)
        emote.count = row['count']
        emote.pm_record = row['pm_record']
        emote.tm_record = row['tm_record']
        emote.recalculate()

        return emote

    def add(self, count):
        self.count += count
        self.deque[0] += count
        self.tm += count
        self.needs_sync = True
        if self.tm > self.tm_record:
            self.tm_record = self.tm

    # Recaculate the per-minute and this-minute stats from the deque data
    def recalculate(self):
        cur_sum = sum(self.deque)
        self.tm = cur_sum

        # TODO: Phase out pm_record
        self.pm = cur_sum / 60
        if self.pm > self.pm_record:
            self.pm_record = self.pm

    def sync(self, cursor):
        cursor.execute('UPDATE `tb_emote` SET `deque`=%s, `pm_record`=%s, `tm_record`=%s, `count`=%s WHERE `id`=%s',
                (json.dumps(list(self.deque)), self.pm_record, self.tm_record, self.count, self.id))

    # Call recalculate and shift the deque
    def shift(self):
        self.recalculate()
        self.deque.rotate(1)
        self.deque[60] = 0


class EmoteManager(UserDict):
    def __init__(self, sqlconn):
        UserDict.__init__(self)
        self.sqlconn = sqlconn
        self.custom_data = []

    def get_cursor(self):
        self.sqlconn.ping()
        return self.sqlconn.cursor(pymysql.cursors.DictCursor)

    def get_normal_cursor(self):
        self.sqlconn.ping()
        return self.sqlconn.cursor()

    def sync(self):
        self.sqlconn.autocommit(False)
        cursor = self.get_normal_cursor()
        for emote in [emote for k, emote in self.data.items() if emote.needs_sync]:
            emote.sync(cursor)

        cursor.close()
        self.sqlconn.autocommit(True)

    def shift(self):
        for k, emote in self.data.items():
            emote.shift()

    def load(self):
        self.data = {}
        self.custom_data = []
        cursor = self.get_cursor()

        cursor.execute('SELECT * FROM `tb_emote`')
        for row in cursor:
            emote = Emote.load_from_row(row)
            if row['emote_id']:
                self.data[emote.emote_id] = emote
                self.data[emote.code] = emote
            else:
                self.data['custom_' + emote.code] = emote
                self.custom_data.append(emote)

        cursor.close()

    def __getitem__(self, key):
        if key not in self.data:
            try:
                # We can only dynamically add emotes that are ID-based
                value = int(key)
            except ValueError:
                return None

            log.info('Adding new emote with ID {0}'.format(value))
            self.data[key] = Emote.load(self.get_cursor(), value)

        return self.data[key]

    def find(self, key):
        try:
            emote_id = int(key)
        except ValueError:
            emote_id = None

        if emote_id:
            return self.data[emote_id]
        else:
            key = str(key)
            if key in self.data:
                return self.data[key]
            else:
                for emote in self.custom_data:
                    if emote.code == key:
                        return emote

        return None

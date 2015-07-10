import logging
import pymysql
import re
import json
import collections

log = logging.getLogger('tyggbot')

class Emote:
    def __init__(self):
        self.pm = 0
        self.tm = 0
        self.pm_record = 0
        self.tm_record = 0
        self.count = 0

    @classmethod
    def load_from_row(cls, row):
        emote = cls()
        emote.id = row['id']
        emote.code = row['code']
        emote.regex = re.compile('(?<![^ ]){0}(?![^ ])'.format(re.escape(emote.code)))
        if row['deque']:
            emote.deque = collections.deque(json.loads(row['deque']))
        else:
            emote.deque = collections.deque([0]*61)
        emote.count = row['count']
        emote.pm_record = row['pm_record']
        emote.tm_record = row['tm_record']
        emote.recalculate()

        return emote

    def add(self, count):
        self.count += count
        self.deque[0] += count
        self.tm += count

    # Recaculate the per-minute and this-minute stats from the deque data
    def recalculate(self):
        cur_sum = sum(self.deque)
        self.pm = cur_sum / 60
        self.tm = cur_sum
        if self.pm > self.pm_record: self.pm_record = self.pm
        if self.tm > self.tm_record: self.tm_record = self.tm

    def sync(self, cursor):
        log.info('Syncing emote {0} ({1}, {2})'.format(self.code, self.pm, self.tm))
        cursor.execute('UPDATE `tb_emote` SET `deque`=%s, `pm_record`=%s, `tm_record`=%s, `count`=%s WHERE `id`=%s',
                (json.dumps(list(self.deque)), self.pm_record, self.tm_record, self.count, self.id))

    # Call recalculate and shift the deque
    def shift(self):
        self.recalculate()
        self.deque.rotate(1)
        self.deque[60] = 0

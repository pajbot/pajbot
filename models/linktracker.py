import logging
import datetime
import pymysql
from urllib.parse import urlsplit

log = logging.getLogger('tyggbot')


class LinkTrackerLink:
    @classmethod
    def load(cls, cursor, url):
        link = cls()

        cursor.execute('SELECT * FROM `tb_link_data` WHERE `url`=%s', [url])
        row = cursor.fetchone()
        if row:
            # We found a link matching this URL in the database!
            link.id = row['id']
            link.url = row['url']
            link.times_linked = row['times_linked']
            link.first_linked = row['first_linked']
            link.last_linked = row['last_linked']
            link.needs_sync = False
        else:
            # No link was found with this URL, create a new one!
            link.id = -1
            link.url = url
            link.times_linked = 0
            link.first_linked = datetime.datetime.now()
            link.last_linked = datetime.datetime.now()
            link.needs_sync = False

        return link

    def increment(self):
        self.times_linked += 1
        self.last_linked = datetime.datetime.now()
        self.needs_sync = True

    def sync(self, cursor):
        _first_linked = self.first_linked.strftime('%Y-%m-%d %H:%M:%S')
        _last_linked = self.last_linked.strftime('%Y-%m-%d %H:%M:%S')
        if self.id == -1:
            cursor.execute('INSERT INTO `tb_link_data` (`url`, `times_linked`, `first_linked`, `last_linked`) VALUES (%s, %s, %s, %s)',
                    [self.url, self.times_linked, _first_linked, _last_linked])
            self.id = cursor.lastrowid
        else:
            cursor.execute('UPDATE `tb_link_data` SET `times_linked`=%s, `last_linked`=%s WHERE `id`=%s',
                    [self.times_linked, _last_linked, self.id])


class LinkTracker:
    def __init__(self, sqlconn):
        self.sqlconn = sqlconn
        self.links = {}

    def add(self, url):
        url_data = urlsplit(url)
        if url_data.netloc[:4] == 'www.':
            netloc = url_data.netloc[4:]
        else:
            netloc = url_data.netloc
        url = netloc + url_data.path
        if url not in self.links:
            self.links[url] = LinkTrackerLink.load(self.sqlconn.cursor(pymysql.cursors.DictCursor), url)

        self.links[url].increment()

    def sync(self):
        self.sqlconn.autocommit(False)
        cursor = self.sqlconn.cursor()
        for link in [link for k, link in self.links.items() if link.needs_sync]:
            link.sync(cursor)
        cursor.close()
        self.sqlconn.autocommit(True)

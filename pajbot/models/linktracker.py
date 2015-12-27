import datetime
import logging

from pajbot.models.db import DBManager, Base

from urllib.parse import urlsplit
from sqlalchemy import Column, Integer, DateTime
from sqlalchemy.dialects.mysql import TEXT

log = logging.getLogger('pajbot')


class LinkTrackerLink(Base):
    __tablename__ = 'tb_link_data'

    id = Column(Integer, primary_key=True)
    url = Column(TEXT)
    times_linked = Column(Integer)
    first_linked = Column(DateTime)
    last_linked = Column(DateTime)

    def __init__(self, url):
        self.id = None
        self.url = url
        self.times_linked = 0
        self.first_linked = datetime.datetime.now()
        self.last_linked = datetime.datetime.now()

    def increment(self):
        self.times_linked += 1
        self.last_linked = datetime.datetime.now()


class LinkTracker:
    def __init__(self):
        self.db_session = DBManager.create_session()
        self.links = {}

    def add(self, url):
        url_data = urlsplit(url)
        if url_data.netloc[:4] == 'www.':
            netloc = url_data.netloc[4:]
        else:
            netloc = url_data.netloc

        if url_data.path.endswith('/'):
            path = url_data.path[:-1]
        else:
            path = url_data.path

        if len(url_data.query) > 0:
            query = '?' + url_data.query
        else:
            query = ''

        url = netloc + path + query
        if url not in self.links:
            for link in self.db_session.query(LinkTrackerLink).filter_by(url=url):
                self.links[link.url] = link

        if url not in self.links:
            link = LinkTrackerLink(url=url)
            self.db_session.add(link)
            self.links[url] = link

        self.links[url].increment()

    def commit(self):
        self.db_session.commit()

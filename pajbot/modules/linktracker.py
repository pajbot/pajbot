import logging
from urllib.parse import urlsplit

from sqlalchemy_utc import UtcDateTime


from sqlalchemy import Column, INT, TEXT

from pajbot import utils
from pajbot.managers.db import Base
from pajbot.managers.db import DBManager
from pajbot.managers.handler import HandlerManager
from pajbot.modules import BaseModule

log = logging.getLogger(__name__)


class LinkTrackerLink(Base):
    __tablename__ = "link_data"

    id = Column(INT, primary_key=True)
    url = Column(TEXT)
    times_linked = Column(INT)
    first_linked = Column(UtcDateTime())
    last_linked = Column(UtcDateTime())

    def __init__(self, url):
        self.id = None
        self.url = url
        self.times_linked = 0
        now = utils.now()
        self.first_linked = now
        self.last_linked = now

    def increment(self):
        self.times_linked += 1
        self.last_linked = utils.now()


class LinkTrackerModule(BaseModule):

    ID = __name__.split(".")[-1]
    NAME = "Link Tracker"
    DESCRIPTION = "Tracks links to see which links are most frequently posted in your chat"
    ENABLED_DEFAULT = True
    CATEGORY = "Feature"
    SETTINGS = []

    def __init__(self, bot):
        super().__init__(bot)
        self.db_session = None
        self.links = {}

    def on_message(self, whisper, urls, **rest):
        if whisper is False:
            for url in urls:
                self.add_url(url)

    def add_url(self, url):
        if self.db_session is None:
            return
        url_data = urlsplit(url)
        if url_data.netloc[:4] == "www.":
            netloc = url_data.netloc[4:]
        else:
            netloc = url_data.netloc

        if url_data.path.endswith("/"):
            path = url_data.path[:-1]
        else:
            path = url_data.path

        if len(url_data.query) > 0:
            query = "?" + url_data.query
        else:
            query = ""

        url = netloc + path + query
        if url not in self.links:
            for link in self.db_session.query(LinkTrackerLink).filter_by(url=url):
                self.links[link.url] = link

        if url not in self.links:
            link = LinkTrackerLink(url=url)
            self.db_session.add(link)
            self.links[url] = link

        self.links[url].increment()

    def on_commit(self, **rest):
        if self.db_session is not None:
            self.db_session.commit()

    def enable(self, bot):
        HandlerManager.add_handler("on_message", self.on_message, priority=200)
        HandlerManager.add_handler("on_commit", self.on_commit)

        if self.db_session is not None:
            self.db_session.commit()
            self.db_session.close()
            self.db_session = None
            self.links = {}
        self.db_session = DBManager.create_session()

    def disable(self, bot):
        HandlerManager.remove_handler("on_message", self.on_message)
        HandlerManager.remove_handler("on_commit", self.on_commit)

        if self.db_session is not None:
            self.db_session.commit()
            self.db_session.close()
            self.db_session = None
            self.links = {}

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, List, Optional

import datetime
import logging
from urllib.parse import urlsplit

from pajbot import utils
from pajbot.managers.db import Base, DBManager
from pajbot.managers.handler import HandlerManager
from pajbot.modules import BaseModule

from sqlalchemy import Integer
from sqlalchemy.orm import Mapped, Session, mapped_column
from sqlalchemy_utc import UtcDateTime

if TYPE_CHECKING:
    from pajbot.bot import Bot

log = logging.getLogger(__name__)


class LinkTrackerLink(Base):
    __tablename__ = "link_data"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    # TODO: url is actually nullable. Fix with a migration
    url: Mapped[str]
    # TODO: times_linked is actually nullable. Fix with a migration
    times_linked: Mapped[int]
    # TODO: first_linked is actually nullable. Fix with a migration
    first_linked: Mapped[datetime.datetime] = mapped_column(UtcDateTime())
    # TODO: last_linked is actually nullable. Fix with a migration
    last_linked: Mapped[datetime.datetime] = mapped_column(UtcDateTime())

    def __init__(self, url: str) -> None:
        self.url = url
        self.times_linked = 0
        now = utils.now()
        self.first_linked = now
        self.last_linked = now

    def increment(self) -> None:
        self.times_linked += 1
        self.last_linked = utils.now()


class LinkTrackerModule(BaseModule):
    ID = __name__.split(".")[-1]
    NAME = "Link Tracker"
    DESCRIPTION = "Tracks chat to see which links are most frequently posted in your chat"
    ENABLED_DEFAULT = True
    CATEGORY = "Feature"
    SETTINGS: List[Any] = []

    def __init__(self, bot: Optional[Bot]) -> None:
        super().__init__(bot)
        self.db_session: Optional[Session] = None
        self.links: Dict[str, LinkTrackerLink] = {}

    def on_message(self, whisper: bool, urls: List[str], **rest) -> bool:
        if whisper is False:
            for url in urls:
                self.add_url(url)

        return True

    def add_url(self, url: str) -> None:
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

    def on_commit(self, **rest) -> bool:
        if self.db_session is not None:
            self.db_session.commit()

        return True

    def enable(self, bot: Optional[Bot]) -> None:
        if bot is None:
            return

        HandlerManager.add_handler("on_message", self.on_message, priority=200)
        HandlerManager.add_handler("on_commit", self.on_commit)

        if self.db_session is not None:
            self.db_session.commit()
            self.db_session.close()
            self.db_session = None
            self.links = {}
        self.db_session = DBManager.create_session()

    def disable(self, bot: Optional[Bot]) -> None:
        if bot is None:
            return

        HandlerManager.remove_handler("on_message", self.on_message)
        HandlerManager.remove_handler("on_commit", self.on_commit)

        if self.db_session is not None:
            self.db_session.commit()
            self.db_session.close()
            self.db_session = None
            self.links = {}

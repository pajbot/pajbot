import logging

from pajbot.managers.db import Base
from pajbot.utils import time_ago

from sqlalchemy import INT, TEXT, Column
from sqlalchemy_utc import UtcDateTime

log = logging.getLogger(__name__)


class Deck(Base):
    __tablename__ = "deck"

    id = Column(INT, primary_key=True)
    name = Column(TEXT)
    deck_class = Column("class", TEXT)
    link = Column(TEXT, nullable=False)
    first_used = Column(UtcDateTime(), nullable=False)
    last_used = Column(UtcDateTime(), nullable=False)
    times_used = Column(INT, nullable=False, default=1)

    def __init__(self):
        self.id = None
        self.name = ""
        self.deck_class = "undefined"
        self.link = None
        self.times_used = 1

    def set(self, **options):
        self.name = options.get("name", self.name)
        self.deck_class = options.get("class", self.deck_class)
        self.link = options.get("link", self.link)
        self.times_used = options.get("times_used", self.times_used)
        self.first_used = options.get("first_used", self.first_used)
        self.last_used = options.get("last_used", self.last_used)

    @property
    def last_used_ago(self):
        return time_ago(self.last_used, "long")

    @property
    def first_used_ago(self):
        return time_ago(self.last_used, "long")

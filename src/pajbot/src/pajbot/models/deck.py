from typing import Optional

import datetime
import logging

from pajbot import utils
from pajbot.managers.db import Base
from pajbot.utils import time_ago

from sqlalchemy import Integer, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy_utc import UtcDateTime

log = logging.getLogger(__name__)


class Deck(Base):
    __tablename__ = "deck"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[Optional[str]]
    deck_class: Mapped[Optional[str]] = mapped_column("class", Text)
    link: Mapped[str]
    first_used: Mapped[datetime.datetime] = mapped_column(UtcDateTime())
    last_used: Mapped[datetime.datetime] = mapped_column(UtcDateTime())
    times_used: Mapped[int] = mapped_column(Integer, default=1)

    def __init__(self, link: str) -> None:
        self.name = ""
        self.deck_class = "undefined"
        self.link = link
        self.first_used = utils.now()
        self.last_used = utils.now()
        self.times_used = 1

    def set(self, **options) -> None:
        self.name = options.get("name", self.name)
        self.deck_class = options.get("class", self.deck_class)
        self.link = options.get("link", self.link)
        self.times_used = options.get("times_used", self.times_used)
        self.first_used = options.get("first_used", self.first_used)
        self.last_used = options.get("last_used", self.last_used)

    @property
    def last_used_ago(self) -> str:
        return time_ago(self.last_used, "long")

    @property
    def first_used_ago(self) -> str:
        return time_ago(self.last_used, "long")

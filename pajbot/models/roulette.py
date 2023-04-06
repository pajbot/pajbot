"""
Run roulette through chat
Roulette stats should update in the web UI on user profiles
"""
import datetime
import logging

from pajbot import utils
from pajbot.managers.db import Base

from sqlalchemy import ForeignKey, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy_utc import UtcDateTime

log = logging.getLogger(__name__)


class Roulette(Base):
    __tablename__ = "roulette"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[str] = mapped_column(Text, ForeignKey("user.id", ondelete="CASCADE"), index=True)
    created_at: Mapped[datetime.datetime] = mapped_column(UtcDateTime())
    points: Mapped[int]

    def __init__(self, user_id: str, points: int) -> None:
        self.user_id = user_id
        self.created_at = utils.now()
        self.points = points

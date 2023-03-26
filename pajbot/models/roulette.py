import datetime
import logging

from pajbot import utils
from pajbot.managers.db import Base

from sqlalchemy import ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy_utc import UtcDateTime

log = logging.getLogger(__name__)


class Roulette(Base):
    __tablename__ = "roulette"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("user.id", ondelete="CASCADE"), index=True)
    created_at: Mapped[datetime.datetime] = mapped_column(UtcDateTime())
    points: Mapped[int]

    def __init__(self, user_id: int, points: int) -> None:
        self.user_id = user_id
        self.created_at = utils.now()
        self.points = points

"""
Duels for zero points can be made: !duel pajlada
Duels for points can be made: !duel pajlada 5
Duel stats update as expected in the web UI on the user profile page
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Optional

import datetime
import logging

from pajbot import utils
from pajbot.managers.db import Base

from sqlalchemy import ForeignKey, Integer
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy_utc import UtcDateTime

if TYPE_CHECKING:
    from pajbot.models.user import User

log = logging.getLogger(__name__)


class UserDuelStats(Base):
    __tablename__ = "user_duel_stats"

    user_id: Mapped[str] = mapped_column(
        Integer, ForeignKey("user.id", ondelete="CASCADE"), primary_key=True, autoincrement=False
    )
    duels_won: Mapped[int]
    duels_total: Mapped[int]
    points_won: Mapped[int]
    points_lost: Mapped[int]
    last_duel: Mapped[Optional[datetime.datetime]] = mapped_column(UtcDateTime())
    current_streak: Mapped[int]
    longest_winstreak: Mapped[int]
    longest_losestreak: Mapped[int]

    def __init__(self) -> None:
        self.duels_won = 0
        self.duels_total = 0
        self.points_won = 0
        self.points_lost = 0
        self.last_duel = None
        self.current_streak = 0
        self.longest_winstreak = 0
        self.longest_losestreak = 0

    user: Mapped[User] = relationship("User", cascade="save-update, merge", lazy="joined", back_populates="_duel_stats")

    @hybrid_property
    def duels_lost(self) -> int:
        return self.duels_total - self.duels_won

    @hybrid_property
    def winrate(self) -> float:
        return self.duels_won * 100 / self.duels_total

    @hybrid_property
    def profit(self) -> int:
        return self.points_won - self.points_lost

    def won(self, points_won: int) -> None:
        self.duels_won += 1
        self.duels_total += 1
        self.points_won += points_won
        self.last_duel = utils.now()

        if self.current_streak > 0:
            self.current_streak += 1
        else:
            self.current_streak = 1
        if self.current_streak > self.longest_winstreak:
            self.longest_winstreak = self.current_streak

    def lost(self, points_lost: int) -> None:
        self.duels_total += 1
        self.points_lost += points_lost
        self.last_duel = utils.now()

        if self.current_streak < 0:
            self.current_streak -= 1
        else:
            self.current_streak = -1
        if abs(self.current_streak) > self.longest_losestreak:
            self.longest_losestreak = self.current_streak

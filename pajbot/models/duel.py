import logging

from sqlalchemy import Column, INT
from sqlalchemy import ForeignKey
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import backref
from sqlalchemy.orm import relationship
from sqlalchemy_utc import UtcDateTime

from pajbot import utils
from pajbot.managers.db import Base

log = logging.getLogger(__name__)


class UserDuelStats(Base):
    __tablename__ = "user_duel_stats"

    user_id = Column(INT, ForeignKey("user.id", ondelete="CASCADE"), primary_key=True, autoincrement=False)
    duels_won = Column(INT, nullable=False, default=0)
    duels_total = Column(INT, nullable=False, default=0)
    points_won = Column(INT, nullable=False, default=0)
    points_lost = Column(INT, nullable=False, default=0)
    last_duel = Column(UtcDateTime(), nullable=True)
    current_streak = Column(INT, nullable=False, default=0)
    longest_winstreak = Column(INT, nullable=False, default=0)
    longest_losestreak = Column(INT, nullable=False, default=0)

    user = relationship(
        "User", cascade="", uselist=False, backref=backref("duel_stats", uselist=False, cascade="", lazy="select")
    )

    @hybrid_property
    def duels_lost(self):
        return self.duels_total - self.duels_won

    @hybrid_property
    def winrate(self):
        return self.duels_won * 100 / self.duels_total

    @hybrid_property
    def profit(self):
        return self.points_won - self.points_lost

    @staticmethod
    def for_user(db_session, user):
        if user.duel_stats is None:
            user.duel_stats = UserDuelStats(user_id=user.id)
            db_session.add(user.duel_stats)
        return user.duel_stats

    def won(self, points_won):
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

    def lost(self, points_lost):
        self.duels_total += 1
        self.points_lost += points_lost
        self.last_duel = utils.now()

        if self.current_streak < 0:
            self.current_streak -= 1
        else:
            self.current_streak = -1
        if abs(self.current_streak) > self.longest_losestreak:
            self.longest_losestreak = self.current_streak

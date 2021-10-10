from __future__ import annotations

import enum

from pajbot import utils
from pajbot.managers.db import Base
from pajbot.models.user import User

import sqlalchemy
from sqlalchemy import INT, Column, ForeignKey, and_, func
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import relationship
from sqlalchemy.sql import functions
from sqlalchemy_utc import UtcDateTime


class HSGameOutcome(enum.Enum):
    win = 0
    loss = 1


HSBetOutcome = sqlalchemy.Enum(HSGameOutcome, name="hsbet_outcome")


class HSBetGame(Base):
    __tablename__ = "hsbet_game"

    # Internal ID
    id = Column(INT, primary_key=True)

    # time when we stop accepting bets
    bet_deadline = Column(UtcDateTime(), nullable=True)

    # ID of the game inside Track-O-Bot. NULL/None if the game has not finished yet.
    trackobot_id = Column(INT, nullable=True, unique=True)
    # outcome of the game. NULL/None if the game has not ended yet
    outcome = Column(HSBetOutcome, nullable=True)

    bets = relationship(
        "HSBetBet", back_populates="game", cascade="all, delete-orphan", passive_deletes=True, collection_class=set
    )

    @hybrid_property
    def is_running(self):
        return self.outcome is None

    @is_running.expression  # type: ignore
    def is_running(self):
        return self.outcome.is_(None)

    @hybrid_property
    def betting_open(self):
        return self.is_running and self.bet_deadline is not None and self.bet_deadline >= utils.now()

    @betting_open.expression  # type: ignore
    def betting_open(self):
        return and_(self.is_running, self.bet_deadline.isnot(None), self.bet_deadline >= functions.now())

    def get_points_by_outcome(self, db_session):
        """Returns how many points are bet on win and how many points
        are bet on lose"""

        rows = (
            db_session.query(HSBetBet.outcome, func.sum(HSBetBet.points))
            .filter_by(game_id=self.id)
            .group_by(HSBetBet.outcome)
            .all()
        )

        points = {key: 0 for key in HSGameOutcome}
        for outcome, num_points in rows:
            points[outcome] = num_points

        return points

    def get_bets_by_outcome(self, db_session):
        """Returns how many bets are bet on win and how many bets
        are bet on lose"""

        rows = (
            db_session.query(HSBetBet.outcome, func.count()).filter_by(game_id=self.id).group_by(HSBetBet.outcome).all()
        )

        bets = {key: 0 for key in HSGameOutcome}
        for outcome, num_bets in rows:
            bets[outcome] = num_bets

        return bets


class HSBetBet(Base):
    __tablename__ = "hsbet_bet"

    # combined PRIMARY KEY(game_id, user_id)
    game_id = Column(INT, ForeignKey("hsbet_game.id", ondelete="CASCADE"), primary_key=True, index=True)
    user_id = Column(INT, ForeignKey("user.id", ondelete="CASCADE"), primary_key=True, index=True)
    outcome = Column(HSBetOutcome, nullable=False)
    points = Column(INT, nullable=False)
    profit = Column(INT, nullable=True)

    user = relationship(User)
    game = relationship(HSBetGame, back_populates="bets")

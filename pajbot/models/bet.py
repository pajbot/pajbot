import enum

import sqlalchemy
from sqlalchemy import BOOLEAN
from sqlalchemy import INT
from sqlalchemy import Column
from sqlalchemy import ForeignKey
from sqlalchemy import and_
from sqlalchemy import func
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import relationship
from sqlalchemy_utc import UtcDateTime

from pajbot import utils
from pajbot.managers.db import Base


class BetGameOutcome(enum.Enum):
    win = 0
    loss = 1


BetOutcome = sqlalchemy.Enum(BetGameOutcome, name="bet_outcome")


class BetGame(Base):
    __tablename__ = "bet_game"

    # ID
    id = Column(INT, primary_key=True)

    # Timestamp
    timestamp = Column(UtcDateTime(), nullable=False)

    # outcome of the bet. NULL/None if the bet has not ended yet
    outcome = Column(BetOutcome, nullable=True)

    # Is the bet closed?
    bets_closed = Column(BOOLEAN, nullable=False, default=False)

    bets = relationship(
        "BetBet", back_populates="game", cascade="all, delete-orphan", passive_deletes=True, collection_class=set
    )

    @hybrid_property
    def is_running(self):
        return self.outcome is None

    @is_running.expression
    def is_running(self):
        return self.outcome.is_(None)

    @hybrid_property
    def betting_open(self):  # Remove 'and not None' check since it's not nullable
        return self.is_running and self.bets_closed is False

    @betting_open.expression
    def betting_open(self):
        return and_(self.is_running, self.bets_closed.is_(False))

    def get_points_by_outcome(self, db_session):
        """ Returns how many points are bet on win and how many points
        are bet on lose """

        rows = (
            db_session.query(BetBet.outcome, func.sum(BetBet.points))
            .filter_by(game_id=self.id)
            .group_by(BetBet.outcome)
            .all()
        )

        points = {key: 0 for key in BetGameOutcome}
        for outcome, num_points in rows:
            points[outcome] = num_points

        return points

    def get_bets_by_outcome(self, db_session):
        """ Returns how many bets are bet on win and how many bets
        are bet on lose """

        rows = db_session.query(BetBet.outcome, func.count()).filter_by(game_id=self.id).group_by(BetBet.outcome).all()

        bets = {key: 0 for key in BetGameOutcome}
        for outcome, num_bets in rows:
            bets[outcome] = num_bets

        return bets

    def __init__(self):
        self.timestamp = utils.now()


class BetBet(Base):
    __tablename__ = "bet_bet"

    # combined PRIMARY KEY(game_id, user_id)
    game_id = Column(INT, ForeignKey("bet_game.id", ondelete="CASCADE"), primary_key=True, index=True)
    user_id = Column(INT, ForeignKey("user.id", ondelete="CASCADE"), primary_key=True, index=True)
    outcome = Column(BetOutcome, nullable=False)
    points = Column(INT, nullable=False)
    profit = Column(INT, nullable=True)

    user = relationship("User")
    game = relationship("BetGame", back_populates="bets")

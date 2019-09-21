import logging

from sqlalchemy import Column, INT
from sqlalchemy import Enum
from sqlalchemy import ForeignKey

from pajbot.managers.db import Base

log = logging.getLogger("pajbot")


class HSBetGame(Base):
    __tablename__ = "hsbet_game"

    id = Column(INT, primary_key=True)
    internal_id = Column(INT, nullable=False)
    outcome = Column(Enum("win", "loss", name="hsbet_outcome"), nullable=False)

    def __init__(self, internal_id, outcome):
        self.internal_id = internal_id
        self.outcome = outcome


class HSBetBet(Base):
    __tablename__ = "hsbet_bet"

    id = Column(INT, primary_key=True)
    game_id = Column(INT, ForeignKey("hsbet_game.id"), nullable=False, index=True)
    user_id = Column(INT, nullable=False, index=True)
    outcome = Column(Enum("win", "loss", name="hsbet_outcome"), nullable=False)
    points = Column(INT, nullable=False)
    profit = Column(INT, nullable=False)

    def __init__(self, game_id, user_id, outcome, points, profit):
        self.game_id = game_id
        self.user_id = user_id
        self.outcome = outcome
        self.points = points
        self.profit = profit

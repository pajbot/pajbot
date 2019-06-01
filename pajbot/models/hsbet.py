import logging

from sqlalchemy import Column
from sqlalchemy import Enum
from sqlalchemy import ForeignKey
from sqlalchemy import Integer

from pajbot.managers.db import Base

log = logging.getLogger("pajbot")


class HSBetGame(Base):
    __tablename__ = "tb_hsbet_game"

    id = Column(Integer, primary_key=True)
    internal_id = Column(Integer, nullable=False)
    outcome = Column(Enum("win", "loss", name="win_or_loss"), nullable=False)

    def __init__(self, internal_id, outcome):
        self.internal_id = internal_id
        self.outcome = outcome


class HSBetBet(Base):
    __tablename__ = "tb_hsbet_bet"

    id = Column(Integer, primary_key=True)
    game_id = Column(Integer, ForeignKey("tb_hsbet_game.id"), nullable=False, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    outcome = Column(Enum("win", "loss", name="win_or_loss"), nullable=False)
    points = Column(Integer, nullable=False)
    profit = Column(Integer, nullable=False)

    def __init__(self, game_id, user_id, outcome, points, profit):
        self.game_id = game_id
        self.user_id = user_id
        self.outcome = outcome
        self.points = points
        self.profit = profit

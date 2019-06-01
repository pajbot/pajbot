from sqlalchemy import TEXT
from sqlalchemy import Boolean
from sqlalchemy import Column
from sqlalchemy import Integer
from sqlalchemy import String

from pajbot.managers.db import Base


class Playsound(Base):
    __tablename__ = "tb_playsound"

    name = Column(String(190), primary_key=True, nullable=False)
    # todo aliases?
    link = Column(TEXT, nullable=False)
    # from 0 to 100
    volume = Column(Integer, nullable=False, default=100)
    cooldown = Column(Integer, nullable=True)
    enabled = Column(Boolean, nullable=False, default=True)

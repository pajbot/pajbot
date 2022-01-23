from pajbot.managers.db import Base

from sqlalchemy import BOOLEAN, INT, TEXT, Column


class Playsound(Base):
    __tablename__ = "playsound"

    name = Column(TEXT, primary_key=True, nullable=False)
    # todo aliases?
    link = Column(TEXT, nullable=False)
    # from 0 to 100
    volume = Column(INT, nullable=False, default=100)
    cooldown = Column(INT, nullable=True)
    enabled = Column(BOOLEAN, nullable=False, default=True)

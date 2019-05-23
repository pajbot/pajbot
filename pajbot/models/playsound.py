from sqlalchemy import Column, String, Integer, Boolean

from pajbot.managers.db import Base


class Playsound(Base):
    __tablename__ = 'tb_playsound'

    name = Column(String(256), primary_key=True, nullable=False)
    # todo aliases?
    link = Column(String(65535), nullable=False)
    # from 0 to 100
    volume = Column(Integer, nullable=False, default=100)
    cooldown = Column(Integer, nullable=True)
    enabled = Column(Boolean, nullable=False, default=True)

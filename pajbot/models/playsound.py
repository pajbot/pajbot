"""
Playsounds can be created through chat
Playsounds can be created through the web UI
Playsounds can be updated through chat
Playsounds can be updated through the web UI
Playsounds can be deleted through chat
Playsounds can be deleted through the web UI
Playsounds can be played through chat
Playsounds can be viewed in the web UI
"""
from typing import Optional

from pajbot.managers.db import Base

from sqlalchemy import Boolean, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column


class Playsound(Base):
    __tablename__ = "playsound"

    name: Mapped[str] = mapped_column(Text, primary_key=True)
    # todo aliases?
    link: Mapped[str]
    # from 0 to 100
    volume: Mapped[int] = mapped_column(Integer, default=100)
    cooldown: Mapped[Optional[int]]
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)

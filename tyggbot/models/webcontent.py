import logging

from tyggbot.models.db import Base

from sqlalchemy import Column, Integer, String, Text

log = logging.getLogger('tyggbot')


class WebContent(Base):
    __tablename__ = 'tb_web_content'

    id = Column(Integer, primary_key=True)
    page = Column(String(64), nullable=False)
    content = Column(Text, nullable=True)

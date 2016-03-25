import logging

from sqlalchemy import Column
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import Text

from pajbot.managers import Base

log = logging.getLogger('pajbot')


class WebContent(Base):
    __tablename__ = 'tb_web_content'

    id = Column(Integer, primary_key=True)
    page = Column(String(64), nullable=False)
    content = Column(Text, nullable=True)

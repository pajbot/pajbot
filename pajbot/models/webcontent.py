from sqlalchemy import Column, INT, TEXT

from pajbot.managers.db import Base


class WebContent(Base):
    __tablename__ = "web_content"

    id = Column(INT, primary_key=True)
    page = Column(TEXT, nullable=False)
    content = Column(TEXT, nullable=True)

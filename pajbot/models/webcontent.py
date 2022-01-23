from pajbot.managers.db import Base

from sqlalchemy import INT, TEXT, Column


class WebContent(Base):
    __tablename__ = "web_content"

    id = Column(INT, primary_key=True)
    page = Column(TEXT, nullable=False)
    content = Column(TEXT, nullable=True)

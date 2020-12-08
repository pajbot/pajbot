import logging

from sqlalchemy import TEXT, INT
from sqlalchemy import Column
from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship

from pajbot.managers.db import Base
from pajbot import utils

log = logging.getLogger(__name__)


class WebSocket(Base):
    __tablename__ = "websockets"

    id = Column(INT, primary_key=True, autoincrement=True)
    salt = Column(TEXT, nullable=False, unique=True)
    widget_id = Column(INT, ForeignKey("widgets.id", ondelete="CASCADE"))
    widget = relationship("Widget")

    def jsonify(self):
        return {"id": self.id, "salt": self.salt, "widget_id": self.widget_id, "widget_name": self.widget.name}

    def new_salt(self, db_session, salt=None):
        if not salt:
            salt = utils.salt_gen(8)
        self.salt = salt
        db_session.merge(self)
        return self

    def remove(self, db_session):
        db_session.delete(self)

    @staticmethod
    def create(db_session, widget_id, salt=None):
        if not salt:
            salt = utils.salt_gen(8)
        websocket = WebSocket(widget_id=widget_id, salt=salt)
        db_session.add(websocket)
        return websocket


class Widget(Base):
    __tablename__ = "widgets"

    id = Column(INT, primary_key=True, autoincrement=True)
    name = Column(TEXT, nullable=False)

    def jsonify(self):
        return {"id": self.id, "name": self.name}

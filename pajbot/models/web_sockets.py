import logging

import random

from sqlalchemy import TEXT, INT
from sqlalchemy import Column
from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship

from pajbot.managers.db import Base

log = logging.getLogger(__name__)

def salt_gen():
    ALPHABET = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
    return "".join(random.choice(ALPHABET) for i in range(8))


class WebSocket(Base):
    __tablename__ = "websockets"

    id = Column(INT, primary_key=True, autoincrement=True)
    salt = Column(TEXT, nullable=False, unique=True)
    widget_id = Column(INT, ForeignKey("widgets.id", ondelete="CASCADE"))
    widget = relationship("Widget")

    def jsonify(self):
        return {
            "id": self.id,
            "salt": self.salt,
            "widget_id": self.widget_id,
            "widget_name": self.widget.name,
        }

    def _new_salt(self, db_session, salt=None):
        if not salt:
            salt = salt_gen()
        self.salt = salt
        db_session.merge(self)
        return self

    def _remove(self, db_session):
        db_session.delete(self)

    @staticmethod
    def _create(db_session, widget_id, salt=None):
        if not salt:
            salt = salt_gen()
        websocket = WebSocket(
            widget_id=widget_id,
            salt=salt,
        )
        db_session.add(websocket)
        return websocket

    @staticmethod
    def _by_id(db_session, id):
        return db_session.query(WebSocket).filter_by(id=id).one_or_none()

    @staticmethod
    def _by_salt(db_session, salt):
        return db_session.query(WebSocket).filter_by(salt=salt).one_or_none()

    @staticmethod
    def _all(db_session):
        return db_session.query(WebSocket).order_by(WebSocket.widget_id, WebSocket.id).all()


class Widget(Base):
    __tablename__ = "widgets"

    id = Column(INT, primary_key=True, autoincrement=True)
    name = Column(TEXT, nullable=False)

    def jsonify(self):
        return {
            "id": self.id,
            "name": self.name,
        }

    @staticmethod
    def _all(db_session):
        return db_session.query(Widget).order_by(Widget.id).all()

    @staticmethod
    def _by_id(db_session, id):
        return db_session.query(Widget).filter_by(id=id).one_or_none()

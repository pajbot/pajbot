import logging

from sqlalchemy import TEXT, INT
from sqlalchemy import Column

from pajbot.managers.db import Base

log = logging.getLogger(__name__)


class WebSocket(Base):
    __tablename__ = "websockets"

    id = Column(INT, primary_key=True, autoincrement=True)
    salt = Column(TEXT, nullable=False, unique=True)

    def jsonify(self):
        return {
            "id": self.id,
            "salt": self.salt,
        }

    def _new_salt(self, db_session, salt=None):
        self.salt = salt
        db_session.merge(self)
        return self

    @staticmethod
    def _create(db_session, salt=None):
        user_con = WebSocket(
            salt=salt,
        )
        db_session.add(user_con)
        return user_con

    @staticmethod
    def _by_id(db_session, id):
        return db_session.query(WebSocket).filter_by(id=id).one_or_none()

    @staticmethod
    def _by_salt(db_session, salt):
        return db_session.query(WebSocket).filter_by(salt=salt).one_or_none()

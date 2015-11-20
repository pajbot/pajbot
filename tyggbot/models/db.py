import logging

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

log = logging.getLogger('tyggbot')


class DBManager:
    def init(url):
        DBManager.engine = create_engine(url)
        DBManager.Session = sessionmaker(bind=DBManager.engine)

    def create_session(**options):
        """
        Useful options:
        expire_on_commit=False
        """

        try:
            return DBManager.Session(**options)
        except:
            log.exception('Unhandled exception while creating a session')

        return None

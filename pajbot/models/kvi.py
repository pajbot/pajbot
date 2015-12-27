import logging
from collections import UserDict

from pajbot.models.db import DBManager, Base

from sqlalchemy import Column, Integer, String

log = logging.getLogger('pajbot')


class KVIData(Base):
    __tablename__ = 'tb_idata'

    id = Column(String(64), primary_key=True)
    value = Column(Integer)

    def __init__(self, id):
        self.id = id
        self.value = 0

    def set(self, new_value):
        self.value = new_value

    def get(self):
        return self.value

    def inc(self):
        self.value += 1

    def dec(self):
        self.value -= 1

    def __str__(self):
        return str(self.value)


class KVIManager(UserDict):
    def __init__(self):
        UserDict.__init__(self)
        self.db_session = DBManager.create_session()

    def __getitem__(self, id):
        if id not in self.data:
            kvidata = KVIData(id)
            self.db_session.add(KVIData(id))
            self.data[id] = kvidata

        return self.data[id]

    def commit(self):
        self.db_session.commit()

    def reload(self):
        self.data = {}
        num_values = 0
        for kvdata in self.db_session.query(KVIData):
            num_values += 1
            self.data[kvdata.id] = kvdata

        log.info('Loaded {0} KVIData values'.format(num_values))
        return self

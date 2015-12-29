import json
import time
import logging
from collections import UserDict
import argparse
import datetime
import re

from pajbot.tbutil import find
from pajbot.models.db import DBManager, Base
from pajbot.models.action import ActionParser, RawFuncAction, FuncAction

import sqlalchemy
from sqlalchemy import orm
from sqlalchemy.orm import relationship, joinedload
from sqlalchemy import Column, Integer, Boolean, DateTime, ForeignKey, String
from sqlalchemy.dialects.mysql import TEXT

log = logging.getLogger('pajbot')

class Module(Base):
    __tablename__ = 'tb_module'

    id = Column(String(64), primary_key=True)
    enabled = Column(Boolean,
            nullable=False,
            default=False,
            server_default=sqlalchemy.sql.expression.false())
    settings = Column(TEXT,
            nullable=True,
            default=None,
            server_default=sqlalchemy.sql.expression.null())

    def __init__(self, id, **options):
        self.id = id
        self.enabled = options.get('enabled', False)
        self.settings = None

class ModuleManager:
    def __init__(self, socket_manager):
        self.modules = []

        if socket_manager:
            socket_manager.add_handler('module.update', self.on_module_reload)

    def on_module_reload(self, data, conn):
        log.info('ModuleManager: module.update begin')
        self.reload()
        log.info('ModuleManager: module.update done')

    def load(self, do_reload=True):
        """ Load module classes """

        from pajbot.modules import available_modules

        self.all_modules = [module() for module in available_modules]

        with DBManager.create_session_scope() as db_session:
            # Make sure there's a row in the DB for each module that's available
            db_modules = db_session.query(Module).all()
            for module in self.all_modules:
                mod = find(lambda m: m.id == module.ID, db_modules)
                if mod is None:
                    log.info('Creating row in DB for module {}'.format(module.ID))
                    mod = Module(module.ID)
                    db_session.add(mod)

        if do_reload is True:
            self.reload()

        return self

    def reload(self):
        self.modules = []

        with DBManager.create_session_scope() as db_session:
            for enabled_module in db_session.query(Module).filter_by(enabled=True):
                module = find(lambda m: m.ID == enabled_module.id, self.all_modules)
                if module is not None:
                    self.modules.append(module.load())

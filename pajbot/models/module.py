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

class ModuleManager:
    def __init__(self, socket_manager):
        self.modules = []

        if socket_manager:
            socket_manager.add_handler('module.reload', self.on_module_reload)

    def on_module_reload(self, data, conn):
        self.reload()

    def load(self):
        """ Load module classes """

        from pajbot.modules import available_modules

        self.all_modules = [module() for module in available_modules]

        self.reload()

        return self

    def reload(self):
        self.modules = []

        with DBManager.create_session_scope() as db_session:
            for enabled_module in db_session.query(Module):
                module = find(lambda m: m.ID == enabled_module.id, self.all_modules)
                if module is not None:
                    self.modules.append(module.load())

import json
import logging
import re

from sqlalchemy import Boolean
from sqlalchemy import Column
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy.dialects.mysql import TEXT
from sqlalchemy.orm import reconstructor

from pajbot.managers.db import Base
from pajbot.models.action import ActionParser

log = logging.getLogger(__name__)


class Filter(Base):
    __tablename__ = 'tb_filters'

    id = Column(Integer, primary_key=True)
    name = Column(String(128))
    type = Column(String(64))
    action_json = Column('action', TEXT)
    extra_extra_args = Column('extra_args', TEXT)
    filter = Column(TEXT)
    source = Column(TEXT)
    enabled = Column(Boolean)
    num_uses = Column(Integer)

    DEFAULT_TIMEOUT_LENGTH = 300
    DEFAULT_NOTIFY = True

    def __init__(self, action, filter, **options):
        self.id = None
        self.name = 'Filter'
        self.type = 'banphrase'
        self.extra_extra_args = None
        self.num_uses = 0
        self.enabled = True
        self.regex = None
        self.set(action=action, filter=filter, **options)

    def set(self, **options):
        self.extra_args = {'filter': self}
        if 'name' in options:
            self.name = options['name']
        if 'action' in options:
            self.action_json = json.dumps(options['action'])
            self.action_parsed_json = options['action']
            self.action = ActionParser.parse(self.action_json)
        if 'filter' in options:
            self.filter = options['filter']
        if 'type' in options:
            self.type = options['type']
        if 'extra_args' in options:
            self.extra_extra_args = json.dumps(options['extra_args'])
            self.extra_args.update(options['extra_args'])
        if 'enabled' in options:
            self.enabled = options['enabled']
        if 'num_users' in options:
            self.num_uses = options['num_uses']

    @reconstructor
    def init_on_load(self):
        self.action_parsed_json = json.loads(self.action_json)
        self.action = ActionParser.parse(self.action_json)
        self.extra_args = {'filter': self}
        self.regex = None
        if self.extra_extra_args:
            try:
                self.extra_args.update(json.loads(self.extra_extra_args))
            except:
                log.exception('Unhandled exception caught while loading Filter extra arguments ({0})'.format(self.extra_extra_args))
        try:
            self.regex = re.compile(self.filter.lower())
        except Exception:
            log.exception('Uncaught exception in filter {0}'.format(self.name))

    def is_enabled(self):
        return self.enabled == 1 and self.action is not None and (self.regex is not None or not self.type == 'regex')

    def match(self, source, message):
        if not self.source or self.source == source:
            return self.regex.match(message)

    def search(self, source, message):
        if not self.source or self.source == source.username:
            return self.regex.search(message)

        return None

    def run(self, bot, source, message, event={}, args={}):
        args.update(self.extra_args)
        self.action.run(bot, source, message, event, args)
        self.num_uses += 1

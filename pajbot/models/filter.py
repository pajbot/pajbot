import json
import re
import argparse
import logging
from collections import UserList

from pajbot.models.db import DBManager, Base
from pajbot.models.action import ActionParser

from sqlalchemy import orm
from sqlalchemy import Column, Integer, String, Boolean
from sqlalchemy.dialects.mysql import TEXT

log = logging.getLogger('pajbot')


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

    @orm.reconstructor
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


class FilterManager(UserList):
    def __init__(self):
        UserList.__init__(self)
        self.db_session = DBManager.create_session()

    def commit(self):
        self.db_session.commit()

    def reload(self):
        self.data = []
        num_filters = 0
        for filter in self.db_session.query(Filter).filter_by(enabled=True):
            num_filters += 1
            self.data.append(filter)

        log.info('Loaded {0} filters'.format(num_filters))
        return self

    def get(self, id=None, phrase=None):
        if id is not None:
            for filter in self.data:
                if filter.id == id:
                    return filter
        elif phrase is not None:
            for filter in self.data:
                if filter.type == 'banphrase' and filter.filter == phrase:
                    return filter
        return None

    def add_banphrase(self, phrase, **options):
        for filter in self.data:
            if filter.filter == phrase and filter.type == 'banphrase':
                # Banphrase already exists
                return filter, False

        default_action = {
                'type': 'func',
                'cb': 'timeout_source'
                }

        filter = Filter(action=options.get('action', default_action),
            filter=phrase,
            name=options.get('name', 'Banphrase'),
            type='banphrase',
            extra_args={
                'time': options.get('time', Filter.DEFAULT_TIMEOUT_LENGTH),
                'notify': options.get('notify', True),
                }
            )
        self.data.append(filter)
        self.db_session.add(filter)
        self.db_session.commit()
        return filter, True

    def remove_filter(self, filter):
        self.db_session.delete(filter)
        self.data.remove(filter)

    def parse_banphrase_arguments(self, message):
        parser = argparse.ArgumentParser()
        parser.add_argument('--length', dest='time', type=int)
        parser.add_argument('--time', dest='time', type=int)
        parser.add_argument('--duration', dest='time', type=int)
        parser.add_argument('--notify', dest='notify', action='store_true')
        parser.add_argument('--no-notify', dest='notify', action='store_false')
        parser.add_argument('--perma', dest='perma', action='store_true')
        parser.add_argument('--no-perma', dest='perma', action='store_false')
        parser.set_defaults(time=None, perma=None, notify=None)

        try:
            args, unknown = parser.parse_known_args(message.split())
        except SystemExit:
            return False, False
        except:
            log.exception('Unhandled exception in add_command')
            return False, False

        # Strip options of any values that are set as None
        options = {k: v for k, v in vars(args).items() if v is not None}
        response = ' '.join(unknown)

        return options, response

import argparse
import logging
from collections import UserList

from pajbot.managers.db import DBManager
from pajbot.models.filter import Filter

log = logging.getLogger(__name__)


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

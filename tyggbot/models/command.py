import json
import time
import logging
from collections import UserDict
import argparse
import datetime

from tyggbot.models.db import DBManager, Base
from tyggbot.models.action import parse_action, RawFuncAction, FuncAction

from sqlalchemy import orm
from sqlalchemy import Column, Integer, Boolean, DateTime
from sqlalchemy.dialects.mysql import TEXT

log = logging.getLogger('tyggbot')


class Command(Base):
    __tablename__ = 'tb_commands'

    id = Column(Integer, primary_key=True)
    level = Column(Integer)
    action_json = Column('action', TEXT)
    extra_extra_args = Column('extra_args', TEXT)
    command = Column(TEXT)
    description = Column(TEXT)
    delay_all = Column(Integer)
    delay_user = Column(Integer)
    enabled = Column(Boolean)
    num_uses = Column(Integer)
    cost = Column(Integer)
    can_execute_with_whisper = Column(Boolean)
    sub_only = Column(Boolean)
    created = Column(DateTime)
    last_updated = Column(DateTime)

    MIN_WHISPER_LEVEL = 420
    BYPASS_DELAY_LEVEL = 2000
    BYPASS_SUB_ONLY_LEVEL = 500

    DEFAULT_CD_ALL = 5
    DEFAULT_CD_USER = 15
    DEFAULT_LEVEL = 100

    def __init__(self):
        self.id = None
        self.level = 100
        self.action = None
        self.extra_args = {'command': self}
        self.delay_all = Command.DEFAULT_CD_ALL
        self.delay_user = Command.DEFAULT_CD_USER
        self.num_uses = 0
        self.level = Command.DEFAULT_LEVEL
        self.enabled = True
        self.type = '?'
        self.cost = 0
        self.can_execute_with_whisper = False
        self.sub_only = False
        self.created = datetime.datetime.now()
        self.last_updated = datetime.datetime.now()

        self.last_run = 0
        self.last_run_by_user = {}

    def set(self, **options):
        self.level = options.get('level', self.level)
        if 'action' in options:
            self.action_json = json.dumps(options['action'])
            self.action = parse_action(self.action_json)
        if 'extra_args' in options:
            self.extra_args = {'command': self}
            self.extra_args.update(options['extra_args'])
            self.extra_extra_args = json.dumps(options['extra_args'])
        self.command = options.get('command', self.command)
        self.description = options.get('description', self.description)
        self.delay_all = options.get('delay_all', self.delay_all)
        self.delay_user = options.get('delay_user', self.delay_user)
        self.enabled = options.get('enabled', self.enabled)
        self.cost = options.get('cost', self.cost)
        self.can_execute_with_whisper = options.get('can_execute_with_whisper', self.can_execute_with_whisper)
        self.sub_only = options.get('sub_only', self.sub_only)

    @orm.reconstructor
    def init_on_load(self):
        self.last_run = 0
        self.last_run_by_user = {}
        self.extra_args = {'command': self}
        self.action = parse_action(self.action_json)
        if self.extra_extra_args:
            try:
                self.extra_args.update(json.loads(self.extra_extra_args))
            except:
                log.exception('Unhandled exception caught while loading Command extra arguments ({0})'.format(self.extra_extra_args))

    @classmethod
    def from_json(cls, json):
        cmd = cls()
        if 'level' in json:
            cmd.level = json['level']
        cmd.action = parse_action(data=json['action'])
        return cmd

    @classmethod
    def dispatch_command(cls, cb, level=1000):
        cmd = cls()
        cmd.load_from_db({
            'id': -1,
            'level': level,
            'action': '{"type": "func", "cb":"' + cb + '"}',
            'delay_all': 0,
            'delay_user': 1,
            'extra_args': None,
            })
        return cmd

    @classmethod
    def tyggbot_command(cls, method_name, level=1000):
        from tyggbot.tyggbot import TyggBot
        cmd = cls()
        cmd.level = level
        cmd.can_execute_with_whisper = True
        cmd.action = RawFuncAction(getattr(TyggBot.instance, method_name))
        return cmd

    @classmethod
    def admin_command(cls, action, type='raw_func', level=1000):
        from tyggbot import TyggBot
        cmd = cls()
        cmd.level = level
        cmd.can_execute_with_whisper = True
        if type == 'raw_func':
            cmd.action = RawFuncAction(getattr(TyggBot.instance, action))
        elif type == 'func':
            cmd.action = FuncAction(action)
        else:
            log.error('Unknown admin command type: {0}'.format(type))
            cmd.action = False
        return cmd

    def load_from_db(self, data):
        self.id = data['id']
        self.level = data['level']
        self.action = parse_action(data['action'])
        self.delay_all = data['delay_all']
        self.delay_user = data['delay_user']
        try:
            self.enabled = data['enabled']
        except:
            self.enabled = True

        try:
            self.num_uses = data['num_uses']
        except:
            self.num_uses = 0

        try:
            self.cost = data['cost']
        except:
            self.cost = 0

        try:
            self.can_execute_with_whisper = int(data['can_execute_with_whisper']) == 1
        except:
            self.can_execute_with_whisper = False

        try:
            self.sub_only = int(data['sub_only']) == 1
        except:
            self.sub_only = False

        if data['extra_args']:
            try:
                self.extra_args.update(json.loads(data['extra_args']))
            except Exception as e:
                log.error('Exception caught while loading Filter extra arguments ({0}): {1}'.format(data['extra_args'], e))

    def load_args(self, level, action):
        self.level = level
        self.action = action

    def is_enabled(self):
        return self.enabled == 1 and self.action is not None

    def run(self, tyggbot, source, message, event={}, args={}, whisper=False):
        if self.action is None:
            log.warning('This command is not available.')
            return False

        if source.level < self.level:
            # User does not have a high enough power level to run this command
            return False

        if whisper and self.can_execute_with_whisper is False and source.level < Command.MIN_WHISPER_LEVEL:
            # This user cannot execute the command through a whisper
            return False

        if self.sub_only and source.subscriber is False and source.level < Command.BYPASS_SUB_ONLY_LEVEL:
            # User is now a sub or a moderator, and cannot use the command.
            return False

        cur_time = time.time()
        time_since_last_run = cur_time - self.last_run

        if time_since_last_run < self.delay_all and source.level < Command.BYPASS_DELAY_LEVEL:
            log.debug('Command was run {0:.2f} seconds ago, waiting...'.format(time_since_last_run))
            return False

        time_since_last_run_user = cur_time - self.last_run_by_user.get(source.username, 0)

        if time_since_last_run_user < self.delay_user and source.level < Command.BYPASS_DELAY_LEVEL:
            log.debug('{0} ran command {1:.2f} seconds ago, waiting...'.format(source.username, time_since_last_run_user))
            return False

        if self.cost > 0 and source.points < self.cost:
            # User does not have enough points to use the command
            return False

        args.update(self.extra_args)
        ret = self.action.run(tyggbot, source, message, event, args)
        if ret is not False:
            self.num_uses += 1
            if self.cost > 0:
                # Only spend points if the action did not fail
                if not source.spend(self.cost):
                    # The user does not have enough points to spend!
                    log.warning('{0} used points he does not have.'.format(source.username))
                    return False
            self.last_run = cur_time
            self.last_run_by_user[source.username] = cur_time


class CommandManager(UserDict):
    def __init__(self):
        UserDict.__init__(self)
        self.db_session = DBManager.create_session()

    def commit(self):
        self.db_session.commit()

    def create_command(self, alias_str, **options):
        aliases = alias_str.lower().replace('!', '').split('|')
        main_alias = aliases[0]
        if main_alias in self.data:
            # Command with this alias already exists, return its instance!
            return self.data[main_alias], False

        command = Command()
        command.set(command=alias_str, **options)
        self.db_session.add(command)
        self.add_command(command)
        self.commit()
        return command, True

    def add_command(self, command):
        aliases = command.command.split('|')
        for alias in aliases:
            self.data[alias] = command

        return len(aliases)

    def remove_command(self, command):
        log.info(command)
        aliases = command.command.split('|')
        for alias in aliases:
            if alias in self.data:
                del self.data[alias]
            else:
                log.warning('For some reason, {0} was not in the list of commands when we removed it.'.format(alias))

        self.db_session.delete(command)
        self.db_session.commit()

    def reload(self):
        self.data = {}
        num_commands = 0
        num_aliases = 0
        for command in self.db_session.query(Command).filter_by(enabled=True):
            num_commands += 1
            num_aliases += self.add_command(command)

        self.data['reload'] = Command.dispatch_command('reload', level=1000)
        self.data['commit'] = Command.dispatch_command('commit', level=1000)
        self.data['quit'] = Command.tyggbot_command('quit')
        self.data['ignore'] = Command.dispatch_command('ignore', level=1000)
        self.data['unignore'] = Command.dispatch_command('unignore', level=1000)
        self.data['permaban'] = Command.dispatch_command('permaban', level=1000)
        self.data['unpermaban'] = Command.dispatch_command('unpermaban', level=1000)
        self.data['twitterfollow'] = Command.dispatch_command('twitter_follow', level=1000)
        self.data['twitterunfollow'] = Command.dispatch_command('twitter_unfollow', level=1000)
        self.data['add'] = Command()
        self.data['add'].load_from_db({
            'id': -1,
            'level': 500,
            'action': '{ "type":"multi", "default":"nothing", "args": [ { "level":500, "command":"banphrase", "action": { "type":"func", "cb":"add_banphrase" } }, { "level":500, "command":"win", "action": { "type":"func", "cb":"add_win" } }, { "level":500, "command":"command", "action": { "type":"func", "cb":"add_command" } }, { "level":2000, "command":"funccommand", "action": { "type":"func", "cb":"add_funccommand" } }, { "level":500, "command":"nothing", "action": { "type":"say", "message":"" } }, { "level":500, "command":"alias", "action": { "type":"func", "cb":"add_alias" } }, { "level":500, "command":"link", "action": { "type":"func", "cb":"add_link" } } ] }',
            'delay_all': 0,
            'delay_user': 1,
            'extra_args': None,
            })
        self.data['remove'] = Command()
        self.data['remove'].load_from_db({
            'id': -1,
            'level': 500,
            'action': '{ "type":"multi", "default":"nothing", "args": [ { "level":500, "command":"banphrase", "action": { "type":"func", "cb":"remove_banphrase" } }, { "level":500, "command":"win", "action": { "type":"func", "cb":"remove_win" } }, { "level":500, "command":"command", "action": { "type":"func", "cb":"remove_command" } }, { "level":500, "command":"nothing", "action": { "type":"say", "message":"" } }, { "level":500, "command":"alias", "action": { "type":"func", "cb":"remove_alias" } }, { "level":500, "command":"link", "action": { "type":"func", "cb":"remove_link" } } ] }',
            'delay_all': 0,
            'delay_user': 1,
            'extra_args': None,
            })
        self.data['rem'] = self.data['remove']
        self.data['del'] = self.data['remove']
        self.data['delete'] = self.data['remove']
        self.data['debug'] = Command()
        self.data['debug'].load_from_db({
            'id': -1,
            'level': 250,
            'action': '{ "type":"multi", "default":"nothing", "args": [ { "level":250, "command":"command", "action": { "type":"func", "cb":"debug_command" } }, { "level":250, "command":"user", "action": { "type":"func", "cb":"debug_user" } }, { "level":250, "command":"nothing", "action": { "type":"say", "message":"" } } ] }',
            'delay_all': 0,
            'delay_user': 1,
            'extra_args': None,
            })
        self.data['level'] = Command.dispatch_command('level', 1000)
        self.data['eval'] = Command.dispatch_command('eval', 2000)

        log.info('Loaded {0} commands with {1} aliases'.format(num_commands, num_aliases))
        return self

    def parse_command_arguments(self, message):
        parser = argparse.ArgumentParser()
        parser.add_argument('--whisper', dest='whisper', action='store_true')
        parser.add_argument('--cd', type=int, dest='delay_all')
        parser.add_argument('--usercd', type=int, dest='delay_user')
        parser.add_argument('--level', type=int, dest='level')

        try:
            args, unknown = parser.parse_known_args(message)
        except SystemExit:
            return False, False
        except:
            log.exception('Unhandled exception in add_command')
            return False, False

        # Strip options of any values that are set as None
        options = {k: v for k, v in vars(args).items() if v is not None}
        response = ' '.join(unknown)

        return options, response

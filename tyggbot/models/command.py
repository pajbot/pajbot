import json
import time
import logging
from collections import UserDict
import argparse
import datetime

from tyggbot.tbutil import find
from tyggbot.models.db import DBManager, Base
from tyggbot.models.action import ActionParser, RawFuncAction, FuncAction

from sqlalchemy import orm
from sqlalchemy.orm import relationship
from sqlalchemy import Column, Integer, Boolean, DateTime, ForeignKey
from sqlalchemy.dialects.mysql import TEXT

log = logging.getLogger('tyggbot')


def parse_command_for_web(alias, command, list):
    import markdown
    from flask import Markup
    if command in list:
        return

    command.json_description = None
    command.parsed_description = ''

    try:
        if command.description is not None:
            command.json_description = json.loads(command.description)
            if 'description' in command.json_description:
                command.parsed_description = Markup(markdown.markdown(command.json_description['description']))
            if command.json_description.get('hidden', False) is True:
                return
    except ValueError:
        # Invalid JSON
        pass
    except:
        log.warn(command.json_description)
        log.exception('Unhandled exception BabyRage')
        return

    if command.command is None:
        command.command = alias

    if command.action is not None and command.action.type == 'multi':
        if command.command is not None:
            command.main_alias = command.command.split('|')[0]
        for inner_alias, inner_command in command.action.commands.items():
            parse_command_for_web(alias if command.command is None else command.main_alias + ' ' + inner_alias, inner_command, list)
    else:
        command.main_alias = '!' + command.command.split('|')[0]
        if len(command.parsed_description) == 0:
            if command.action is not None:
                if command.action.type == 'message':
                    command.parsed_description = command.action.response
                    if len(command.action.response) == 0:
                        return
            if command.description is not None:
                command.parsed_description = command.description
        list.append(command)


class CommandData(Base):
    __tablename__ = 'tb_command_data'

    command_id = Column(Integer, ForeignKey('tb_command.id'), primary_key=True, autoincrement=False)
    num_uses = Column(Integer, nullable=False, default=0)

    def __init__(self, command_id, **options):
        self.command_id = command_id

        self.set(**options)

    def set(self, **options):
        self.num_uses = options.get('num_uses', 0)


class Command(Base):
    __tablename__ = 'tb_command'

    id = Column(Integer, primary_key=True)
    level = Column(Integer, nullable=False, default=100)
    action_json = Column('action', TEXT)
    extra_extra_args = Column('extra_args', TEXT)
    command = Column(TEXT, nullable=False)
    description = Column(TEXT, nullable=True)
    delay_all = Column(Integer, nullable=False, default=5)
    delay_user = Column(Integer, nullable=False, default=15)
    enabled = Column(Boolean, nullable=False, default=True)
    cost = Column(Integer, nullable=False, default=0)
    can_execute_with_whisper = Column(Boolean)
    sub_only = Column(Boolean, nullable=False, default=False)
    mod_only = Column(Boolean, nullable=False, default=False)

    data = relationship('CommandData',
            uselist=False,
            lazy='joined')

    MIN_WHISPER_LEVEL = 420
    BYPASS_DELAY_LEVEL = 2000
    BYPASS_SUB_ONLY_LEVEL = 500
    BYPASS_MOD_ONLY_LEVEL = 500

    DEFAULT_CD_ALL = 5
    DEFAULT_CD_USER = 15
    DEFAULT_LEVEL = 100

    def __init__(self, **options):
        self.id = options.get('id', None)

        self.level = Command.DEFAULT_LEVEL
        self.action = None
        self.extra_args = {'command': self}
        self.delay_all = Command.DEFAULT_CD_ALL
        self.delay_user = Command.DEFAULT_CD_USER
        self.description = None
        self.enabled = True
        self.type = '?'  # XXX: What is this?
        self.cost = 0
        self.can_execute_with_whisper = False
        self.sub_only = False
        self.mod_only = False
        self.command = None

        self.last_run = 0
        self.last_run_by_user = {}

        self.data = None

        self.set(**options)

    def set(self, **options):
        self.level = options.get('level', self.level)
        if 'action' in options:
            self.action_json = json.dumps(options['action'])
            self.action = ActionParser.parse(self.action_json)
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
        self.mod_only = options.get('mod_only', self.mod_only)

    @orm.reconstructor
    def init_on_load(self):
        self.last_run = 0
        self.last_run_by_user = {}
        self.extra_args = {'command': self}
        self.action = ActionParser.parse(self.action_json)
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
        cmd.action = ActionParser.parse(data=json['action'])
        return cmd

    @classmethod
    def dispatch_command(cls, cb, **options):
        cmd = cls(**options)
        cmd.action = ActionParser.parse('{"type": "func", "cb": "' + cb + '"}')
        return cmd

    @classmethod
    def tyggbot_command(cls, bot, method_name, level=1000, **options):
        from tyggbot.tyggbot import TyggBot
        cmd = cls()
        cmd.level = level
        cmd.description = options.get('description', None)
        cmd.can_execute_with_whisper = True
        try:
            cmd.action = RawFuncAction(getattr(bot, method_name))
        except:
            pass
        return cmd

    @classmethod
    def multiaction_command(cls, **options):
        from tyggbot.models.action import MultiAction
        cmd = cls(**options)
        cmd.action = MultiAction.ready_built(options.get('commands'))
        return cmd

    def load_args(self, level, action):
        self.level = level
        self.action = action

    def is_enabled(self):
        return self.enabled == 1 and self.action is not None

    def run(self, bot, source, message, event={}, args={}, whisper=False):
        if self.action is None:
            log.warning('This command is not available.')
            return False

        if source.level < self.level:
            # User does not have a high enough power level to run this command
            return False

        if whisper and self.can_execute_with_whisper is False and source.level < Command.MIN_WHISPER_LEVEL and source.moderator is False:
            # This user cannot execute the command through a whisper
            return False

        if self.sub_only and source.subscriber is False and source.level < Command.BYPASS_SUB_ONLY_LEVEL:
            # User is not a sub or a moderator, and cannot use the command.
            return False

        if self.mod_only and source.moderator is False and source.level < Command.BYPASS_MOD_ONLY_LEVEL:
            # User is not a twitch moderator, or a bot moderator
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
        ret = self.action.run(bot, source, message, event, args)
        if ret is not False:
            if self.data is not None:
                self.data.num_uses += 1
            if self.cost > 0:
                # Only spend points if the action did not fail
                if not source.spend(self.cost):
                    # The user does not have enough points to spend!
                    log.warning('{0} used points he does not have.'.format(source.username))
                    return False
            self.last_run = cur_time
            self.last_run_by_user[source.username] = cur_time


class CommandManager(UserDict):
    def __init__(self, bot):
        UserDict.__init__(self)
        self.db_session = DBManager.create_session()
        self.internal_commands = None
        self.bot = bot
        if bot:
            self.bot.socket_manager.add_handler('command.update', self.on_command_update)
            self.bot.socket_manager.add_handler('command.remove', self.on_command_remove)

    def on_command_update(self, data, conn):
        try:
            command_id = int(data['command_id'])
        except (KeyError, ValueError):
            log.warn('No command ID found in on_command_update')
            return False

        command = find(lambda command: command.id == command_id, self.data.values())
        if command is None:
            log.warn('Invalid ID sent to on_command_update')
            return False

        self.remove_command_aliases(command)
        self.load_by_id(command_id)

        log.debug('Update command with id {}'.format(command_id))

    def on_command_remove(self, data, conn):
        try:
            command_id = int(data['command_id'])
        except (KeyError, ValueError):
            log.warn('No command ID found in on_command_update')
            return False

        command = find(lambda command: command.id == command_id, self.data.values())
        if command is None:
            log.warn('Invalid ID sent to on_command_update')
            return False

        self.db_session.expunge(command.data)
        self.remove_command_aliases(command)

        log.debug('Remove command with id {}'.format(command_id))

    def __del__(self):
        self.db_session.close()

    def commit(self):
        self.db_session.commit()

    def get_internal_commands(self):
        if self.internal_commands is not None:
            return self.internal_commands

        try:
            level_trusted_mods = 100 if self.bot.trusted_mods else 500
            mod_only_trusted_mods = True if self.bot.trusted_mods else False
        except AttributeError:
            level_trusted_mods = 500
            mod_only_trusted_mods = False

        self.internal_commands = {}

        self.internal_commands['reload'] = Command.dispatch_command('reload',
                level=1000,
                description='Reload a bunch of data from the database')
        self.internal_commands['commit'] = Command.dispatch_command('commit',
                level=1000,
                description='Commit data from the bot to the database')
        self.internal_commands['quit'] = Command.tyggbot_command(self.bot, 'quit',
                level=1000,
                description='Shut down the bot, this will most definitely restart it if set up properly')
        self.internal_commands['ignore'] = Command.dispatch_command('ignore',
                level=1000,
                description='Ignore a user, which means he can\'t run any commands')
        self.internal_commands['unignore'] = Command.dispatch_command('unignore',
                level=1000,
                description='Unignore a user')
        self.internal_commands['permaban'] = Command.dispatch_command('permaban',
                level=1000,
                description='Permanently ban a user. Every time the user types in chat, he will be permanently banned again')
        self.internal_commands['unpermaban'] = Command.dispatch_command('unpermaban',
                level=1000,
                description='Remove a permanent ban from a user')
        self.internal_commands['twitterfollow'] = Command.dispatch_command('twitter_follow',
                level=1000,
                description='Start listening for tweets for the given user')
        self.internal_commands['twitterunfollow'] = Command.dispatch_command('twitter_unfollow',
                level=1000,
                description='Stop listening for tweets for the given user')
        self.internal_commands['add'] = Command.multiaction_command(
                level=100,
                delay_all=0,
                delay_user=0,
                default=None,
                command='add',
                commands={
                    'command': Command.dispatch_command('add_command',
                        level=500,
                        description='Add a command!'),
                    'banphrase': Command.dispatch_command('add_banphrase',
                        level=500,
                        description='Add a banphrase!'),
                    'win': Command.dispatch_command('add_win',
                        level=500,
                        description='Add a win to something!'),
                    'funccommand': Command.dispatch_command('add_funccommand',
                        level=2000,
                        description='Add a command that uses a command'),
                    'alias': Command.dispatch_command('add_alias',
                        level=500,
                        description='Adds an alias to an already existing command'),
                    'link': Command.multiaction_command(
                        level=500,
                        delay_all=0,
                        delay_user=0,
                        default=None,
                        commands={
                            'blacklist': Command.dispatch_command('add_link_blacklist',
                                level=500,
                                description='Blacklist a link'),
                            'whitelist': Command.dispatch_command('add_link_whitelist',
                                level=500,
                                description='Whitelist a link'),
                            }
                        ),
                    'highlight': Command.dispatch_command('add_highlight',
                        level=100,
                        mod_only=True,
                        description='Creates an highlight at the current timestamp'),
                    })
        self.internal_commands['edit'] = self.internal_commands['add']
        self.internal_commands['remove'] = Command.multiaction_command(
                level=100,
                delay_all=0,
                delay_user=0,
                default=None,
                command='remove',
                commands={
                    'command': Command.dispatch_command('remove_command',
                        level=500,
                        description='Remove a command!'),
                    'banphrase': Command.dispatch_command('remove_banphrase',
                        level=500,
                        description='Remove a banphrase!'),
                    'win': Command.dispatch_command('remove_win',
                        level=500,
                        description='Remove a win to something!'),
                    'alias': Command.dispatch_command('remove_alias',
                        level=500,
                        description='Removes an alias to an already existing command'),
                    'link': Command.multiaction_command(
                        level=500,
                        delay_all=0,
                        delay_user=0,
                        default=None,
                        commands={
                            'blacklist': Command.dispatch_command('remove_link_blacklist',
                                level=500,
                                description='Unblacklist a link'),
                            'whitelist': Command.dispatch_command('remove_link_whitelist',
                                level=500,
                                description='Unwhitelist a link'),
                            }
                        ),
                    'highlight': Command.dispatch_command('remove_highlight',
                        level=level_trusted_mods,
                        mod_only=mod_only_trusted_mods,
                        description='Removes an highlight with the given ID.'),
                    })
        self.internal_commands['rem'] = self.internal_commands['remove']
        self.internal_commands['del'] = self.internal_commands['remove']
        self.internal_commands['delete'] = self.internal_commands['remove']
        self.internal_commands['debug'] = Command.multiaction_command(
                level=250,
                delay_all=0,
                delay_user=0,
                default=None,
                commands={
                    'command': Command.dispatch_command('debug_command',
                        level=250,
                        description='Debug a command'),
                    'user': Command.dispatch_command('debug_user',
                        level=250,
                        description='Debug a user'),
                    })
        self.internal_commands['level'] = Command.dispatch_command('level',
                level=1000,
                description='Set a users level')
        self.internal_commands['eval'] = Command.dispatch_command('eval',
                level=2000,
                description='Run a raw python command. Debug mode only')

        return self.internal_commands

    def create_command(self, alias_str, **options):
        """
        TODO: Does this part of the code work as expected?
        Right now if the second alias is already used, it could result in us
        creating a command with an alias that's already in use.
        """
        aliases = alias_str.lower().replace('!', '').split('|')
        main_alias = aliases[0]
        if main_alias in self.data:
            # Command with this alias already exists, return its instance!
            return self.data[main_alias], False

        command = Command(command=alias_str, **options)
        command.data = CommandData(command.id)
        self.add_command_aliases(command)
        DBManager.session_add_expunge(command)
        self.db_session.add(command.data)
        self.commit()
        return command, True

    def edit_command(self, command, **options):
        command.set(**options)
        DBManager.session_add_expunge(command)

    def remove_command_aliases(self, command):
        aliases = command.command.split('|')
        for alias in aliases:
            if alias in self.data:
                del self.data[alias]
            else:
                log.warning('For some reason, {0} was not in the list of commands when we removed it.'.format(alias))

    def remove_command(self, command):
        self.remove_command_aliases(command)

        with DBManager.create_session_scope() as db_session:
            self.db_session.expunge(command.data)
            db_session.delete(command.data)
            db_session.delete(command)

    def add_command_aliases(self, command):
        aliases = command.command.split('|')
        for alias in aliases:
            self.data[alias] = command

        return len(aliases)

    def load(self):
        self.get_internal_commands()
        self.data = self.internal_commands

        for command in self.db_session.query(Command).filter_by(enabled=True):
            self.add_command_aliases(command)
            self.db_session.expunge(command)
            if command.data is None:
                log.info('Creating command data for {}'.format(command.command))
                command.data = CommandData(command.id)
            self.db_session.add(command.data)

        return self

    def load_by_id(self, command_id):
        self.db_session.commit()
        command = self.db_session.query(Command).filter_by(id=command_id, enabled=True).one_or_none()
        if command:
            self.add_command_aliases(command)
            self.db_session.expunge(command)
            if command.data is None:
                log.info('Creating command data for {}'.format(command.command))
                command.data = CommandData(command.id)
            self.db_session.add(command.data)

    def parse_for_web(self):
        list = []

        for alias, command in self.data.items():
            parse_command_for_web(alias, command, list)

        return list

    def parse_command_arguments(self, message):
        parser = argparse.ArgumentParser()
        parser.add_argument('--whisper', dest='whisper', action='store_true')
        parser.add_argument('--no-whisper', dest='whisper', action='store_false')
        parser.add_argument('--reply', dest='reply', action='store_true')
        parser.add_argument('--no-reply', dest='reply', action='store_false')
        parser.add_argument('--cd', type=int, dest='delay_all')
        parser.add_argument('--usercd', type=int, dest='delay_user')
        parser.add_argument('--level', type=int, dest='level')
        parser.add_argument('--cost', type=int, dest='cost')
        parser.add_argument('--modonly', dest='mod_only', action='store_true')
        parser.add_argument('--no-modonly', dest='mod_only', action='store_false')

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

        if 'cost' in options:
            options['cost'] = abs(options['cost'])

        return options, response

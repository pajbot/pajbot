import argparse
import datetime
import json
import logging
import re
import time
from collections import UserDict

from sqlalchemy import Boolean
from sqlalchemy import Column
from sqlalchemy import DateTime
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy.dialects.mysql import TEXT
from sqlalchemy.orm import joinedload
from sqlalchemy.orm import reconstructor
from sqlalchemy.orm import relationship

from pajbot.managers import Base
from pajbot.managers import DBManager
from pajbot.managers import ScheduleManager
from pajbot.models.action import ActionParser
from pajbot.models.action import RawFuncAction
from pajbot.tbutil import find

log = logging.getLogger('pajbot')


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
        test = re.compile('[^\w]')
        first_alias = command.command.split('|')[0]
        command.resolve_string = test.sub('', first_alias.replace(' ', '_'))
        command.main_alias = '!' + first_alias
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

    added_by = Column(Integer, nullable=True)
    edited_by = Column(Integer, nullable=True)
    last_date_used = Column(DateTime, nullable=True)

    user = relationship(
        'User',
        primaryjoin='User.id==CommandData.edited_by',
        foreign_keys='User.id',
        uselist=False,
        cascade='',
        lazy='noload')

    user2 = relationship(
        'User',
        primaryjoin='User.id==CommandData.added_by',
        foreign_keys='User.id',
        uselist=False,
        cascade='',
        lazy='noload')

    def __init__(self, command_id, **options):
        self.command_id = command_id
        self.num_uses = 0
        self.added_by = None
        self.edited_by = None
        self.last_date_used = 0

        self.set(**options)

    def set(self, **options):
        self.num_uses = options.get('num_uses', self.num_uses)
        self.added_by = options.get('added_by', self.added_by)
        self.edited_by = options.get('edited_by', self.edited_by)
        self.last_date_used = options.get('last_date_used', self.last_date_used)


class CommandExample(Base):
    __tablename__ = 'tb_command_example'

    id = Column(Integer, primary_key=True)
    command_id = Column(Integer, ForeignKey('tb_command.id'), nullable=False)
    title = Column(String(256), nullable=False)
    chat = Column(TEXT, nullable=False)
    description = Column(String(512), nullable=False)

    def __init__(self, command_id, title, chat='', description=''):
        self.id = None
        self.command_id = command_id
        self.title = title
        self.chat = chat
        self.description = description
        self.chat_messages = []

    @reconstructor
    def init_on_load(self):
        self.parse()

    def add_chat_message(self, type, message, user_from, user_to=None):
        chat_message = {
                'source': {
                    'type': type,
                    'from': user_from,
                    'to': user_to
                    },
                'message': message
                }
        self.chat_messages.append(chat_message)

    def parse(self):
        self.chat_messages = []
        for line in self.chat.split('\n'):
            users, message = line.split(':', 1)
            if '>' in users:
                user_from, user_to = users.split('>', 1)
                self.add_chat_message('whisper', message, user_from, user_to=user_to)
            else:
                self.add_chat_message('say', message, users)
        return self

    def jsonify(self):
        return {
                'id': self.id,
                'command_id': self.command_id,
                'title': self.title,
                'description': self.description,
                'messages': self.chat_messages,
                }


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
    tokens_cost = Column(
        Integer,
        nullable=False,
        default=0,
        server_default='0')
    can_execute_with_whisper = Column(Boolean)
    sub_only = Column(Boolean, nullable=False, default=False)
    mod_only = Column(Boolean, nullable=False, default=False)
    long_description = ''

    data = relationship(
        'CommandData',
        uselist=False,
        cascade='',
        lazy='joined')
    examples = relationship(
        'CommandExample',
        uselist=True,
        cascade='',
        lazy='noload')

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
        self.tokens_cost = 0
        self.can_execute_with_whisper = False
        self.sub_only = False
        self.mod_only = False
        self.command = None

        self.last_run = 0
        self.last_run_by_user = {}

        self.data = None
        self.run_in_thread = False

        self.set(**options)

    def set(self, **options):
        self.level = options.get('level', self.level)
        if 'action' in options:
            self.action_json = json.dumps(options['action'])
            self.action = ActionParser.parse(self.action_json, command=self.command)
        if 'extra_args' in options:
            self.extra_args = {'command': self}
            self.extra_args.update(options['extra_args'])
            self.extra_extra_args = json.dumps(options['extra_args'])
        self.command = options.get('command', self.command)
        self.description = options.get('description', self.description)
        self.delay_all = options.get('delay_all', self.delay_all)
        if self.delay_all < 0:
            self.delay_all = 0
        self.delay_user = options.get('delay_user', self.delay_user)
        if self.delay_user < 0:
            self.delay_user = 0
        self.enabled = options.get('enabled', self.enabled)
        self.cost = options.get('cost', self.cost)
        if self.cost < 0:
            self.cost = 0
        self.tokens_cost = options.get('tokens_cost', self.tokens_cost)
        if self.tokens_cost < 0:
            self.tokens_cost = 0
        self.can_execute_with_whisper = options.get('can_execute_with_whisper', self.can_execute_with_whisper)
        self.sub_only = options.get('sub_only', self.sub_only)
        self.mod_only = options.get('mod_only', self.mod_only)
        self.examples = options.get('examples', self.examples)
        self.run_in_thread = options.get('run_in_thread', self.run_in_thread)

    def __str__(self):
        return 'Command(!{})'.format(self.command)

    @reconstructor
    def init_on_load(self):
        self.last_run = 0
        self.last_run_by_user = {}
        self.extra_args = {'command': self}
        self.action = ActionParser.parse(self.action_json, command=self.command)
        self.run_in_thread = False
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
        cmd.action = ActionParser.parse(data=json['action'], command=cmd.command)
        return cmd

    @classmethod
    def dispatch_command(cls, cb, **options):
        cmd = cls(**options)
        cmd.action = ActionParser.parse('{"type": "func", "cb": "' + cb + '"}', command=cmd.command)
        return cmd

    @classmethod
    def raw_command(cls, cb, **options):
        cmd = cls(**options)
        try:
            cmd.action = RawFuncAction(cb)
        except:
            log.exception('Uncaught exception in Command.raw_command. catch the following exception manually!')
            cmd.enabled = False
        return cmd

    @classmethod
    def pajbot_command(cls, bot, method_name, level=1000, **options):
        cmd = cls(**options)
        cmd.level = level
        cmd.description = options.get('description', None)
        cmd.can_execute_with_whisper = True
        try:
            cmd.action = RawFuncAction(getattr(bot, method_name))
        except:
            pass
        return cmd

    @classmethod
    def multiaction_command(cls, default=None, fallback=None, **options):
        from pajbot.models.action import MultiAction
        cmd = cls(**options)
        cmd.action = MultiAction.ready_built(options.get('commands'),
                default=default,
                fallback=fallback)
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

        if self.sub_only and source.subscriber is False and source.level < Command.BYPASS_SUB_ONLY_LEVEL and source.moderator is False:
            # User is not a sub or a moderator, and cannot use the command.
            return False

        if self.mod_only and source.moderator is False and source.level < Command.BYPASS_MOD_ONLY_LEVEL:
            # User is not a twitch moderator, or a bot moderator
            return False

        cd_modifier = 0.2 if source.level >= 500 or source.moderator is True else 1.0

        cur_time = time.time()
        time_since_last_run = (cur_time - self.last_run) / cd_modifier

        if time_since_last_run < self.delay_all and source.level < Command.BYPASS_DELAY_LEVEL:
            log.debug('Command was run {0:.2f} seconds ago, waiting...'.format(time_since_last_run))
            return False

        time_since_last_run_user = (cur_time - self.last_run_by_user.get(source.username, 0)) / cd_modifier

        if time_since_last_run_user < self.delay_user and source.level < Command.BYPASS_DELAY_LEVEL:
            log.debug('{0} ran command {1:.2f} seconds ago, waiting...'.format(source.username, time_since_last_run_user))
            return False

        if self.cost > 0 and not source.can_afford(self.cost):
            # User does not have enough points to use the command
            return False

        if self.tokens_cost > 0 and not source.can_afford_with_tokens(self.tokens_cost):
            # User does not have enough tokens to use the command
            return False

        args.update(self.extra_args)
        if self.run_in_thread:
            log.debug('Running {} in a thread'.format(self))
            ScheduleManager.execute_now(self.run_action, args=[bot, source, message, event, args])
        else:
            self.run_action(bot, source, message, event, args)

    def run_action(self, bot, source, message, event, args):
        cur_time = time.time()
        with source.spend_currency_context(self.cost, self.tokens_cost):
            ret = self.action.run(bot, source, message, event, args)
            if ret is False:
                raise ValueError('return currency')
            else:
                # Only spend points/tokens, and increment num_uses if the action succeded
                if self.data is not None:
                    self.data.num_uses += 1
                    self.data.last_date_used = datetime.datetime.now()
                if self.tokens_cost > 0:
                    if not source.spend_tokens(self.tokens_cost):
                        # The user does not have enough tokens to spend!
                        log.warning('{0} used tokens he does not have.'.format(source.username))
                        return False

                # TODO: Will this be an issue?
                self.last_run = cur_time
                self.last_run_by_user[source.username] = cur_time

    def autogenerate_examples(self):
        if len(self.examples) == 0 and self.id is not None and self.action.type == 'message':
            examples = []
            if self.can_execute_with_whisper is True:
                example = CommandExample(self.id, 'Default usage through whisper')
                subtype = self.action.subtype if self.action.subtype is not 'reply' else 'say'
                example.add_chat_message('whisper', self.main_alias, 'user', 'bot')
                if subtype == 'say' or subtype == 'me':
                    example.add_chat_message(subtype, self.action.response, 'bot')
                elif subtype == 'whisper':
                    example.add_chat_message(subtype, self.action.response, 'bot', 'user')
                examples.append(example)

            example = CommandExample(self.id, 'Default usage')
            subtype = self.action.subtype if self.action.subtype is not 'reply' else 'say'
            example.add_chat_message('say', self.main_alias, 'user')
            if subtype == 'say' or subtype == 'me':
                example.add_chat_message(subtype, self.action.response, 'bot')
            elif subtype == 'whisper':
                example.add_chat_message(subtype, self.action.response, 'bot', 'user')
            examples.append(example)
            return examples
        return self.examples

    def jsonify(self):
        """ jsonify will only be called from the web interface.
        we assume that commands have been run throug the parse_command_for_web method """
        return {
                'id': self.id,
                'level': self.level,
                'aliases': self.command.split('|'),
                'description': self.description,
                'long_description': self.long_description,
                'cd_all': self.delay_all,
                'cd_user': self.delay_user,
                'enabled': self.enabled,
                'cost': self.cost,
                'tokens_cost': self.tokens_cost,
                'can_execute_with_whisper': self.can_execute_with_whisper,
                'sub_only': self.sub_only,
                'mod_only': self.mod_only,
                'resolve_string': self.resolve_string,
                'examples': [example.jsonify() for example in self.autogenerate_examples()],
                }


class CommandManager(UserDict):
    """ This class is responsible for compiling commands from multiple sources
    into one easily accessible source.
    The following sources are used:
     - internal_commands = Commands that are added in source
     - db_commands = Commands that are loaded from the database
     - module_commands = Commands that are loaded from enabled modules

    """

    def __init__(self, socket_manager=None, module_manager=None, bot=None):
        UserDict.__init__(self)
        self.db_session = DBManager.create_session()

        self.internal_commands = {}
        self.db_commands = {}
        self.module_commands = {}

        self.bot = bot
        self.module_manager = module_manager

        if socket_manager:
            socket_manager.add_handler('module.update', self.on_module_reload)
            socket_manager.add_handler('command.update', self.on_command_update)
            socket_manager.add_handler('command.remove', self.on_command_remove)

    def on_module_reload(self, data, conn):
        log.debug('Rebuilding commands...')
        self.rebuild()
        log.debug('Done rebuilding commands')

    def on_command_update(self, data, conn):
        try:
            command_id = int(data['command_id'])
        except (KeyError, ValueError):
            log.warn('No command ID found in on_command_update')
            return False

        command = find(lambda command: command.id == command_id, self.db_commands.values())
        if command is not None:
            self.remove_command_aliases(command)

        self.load_by_id(command_id)

        log.debug('Reloaded command with id {}'.format(command_id))

        self.rebuild()

    def on_command_remove(self, data, conn):
        try:
            command_id = int(data['command_id'])
        except (KeyError, ValueError):
            log.warn('No command ID found in on_command_update')
            return False

        command = find(lambda command: command.id == command_id, self.db_commands.values())
        if command is None:
            log.warn('Invalid ID sent to on_command_update')
            return False

        self.db_session.expunge(command.data)
        self.remove_command_aliases(command)

        log.debug('Remove command with id {}'.format(command_id))

        self.rebuild()

    def __del__(self):
        self.db_session.close()

    def commit(self):
        self.db_session.commit()

    def load_internal_commands(self, **options):
        if len(self.internal_commands) > 0:
            return self.internal_commands

        self.internal_commands = {}

        self.internal_commands['quit'] = Command.pajbot_command(self.bot, 'quit',
                level=1000,
                command='quit',
                description='Shut down the bot, this will most definitely restart it if set up properly')

        self.internal_commands['ceaseallactionscurrentlybeingacteduponwiththecodeandiapologizeforbeingawhitecisgenderedmaleinthepatriarchy'] = self.internal_commands['quit']

        self.internal_commands['twitterfollow'] = Command.dispatch_command('twitter_follow',
                level=1000,
                description='Start listening for tweets for the given user',
                examples=[
                    CommandExample(None, 'Default usage',
                        chat='user:!twitterfollow forsensc2\n'
                        'bot>user:Now following ForsenSC2',
                        description='Follow ForsenSC2 on twitter so new tweets are output in chat.').parse(),
                    ])

        self.internal_commands['twitterunfollow'] = Command.dispatch_command('twitter_unfollow',
                level=1000,
                description='Stop listening for tweets for the given user',
                examples=[
                    CommandExample(None, 'Default usage',
                        chat='user:!twitterunfollow forsensc2\n'
                        'bot>user:No longer following ForsenSC2',
                        description='Stop automatically printing tweets from ForsenSC2').parse(),
                    ])

        self.internal_commands['add'] = Command.multiaction_command(
                level=100,
                delay_all=0,
                delay_user=0,
                default=None,
                command='add',
                commands={
                    'command': Command.dispatch_command('add_command',
                        level=500,
                        description='Add a command!',
                        examples=[
                            CommandExample(None, 'Create a normal command',
                                chat='user:!add command test Kappa 123\n'
                                'bot>user:Added your command (ID: 7)',
                                description='This creates a normal command with the trigger !test which outputs Kappa 123 to chat').parse(),
                            CommandExample(None, 'Create a command that responds with a whisper',
                                chat='user:!add command test Kappa 123 --whisper\n'
                                'bot>user:Added your command (ID: 7)',
                                description='This creates a command with the trigger !test which responds with Kappa 123 as a whisper to the user who called the command').parse(),
                            ]),
                    'win': Command.dispatch_command('add_win',
                        level=500,
                        description='Add a win to something!'),
                    'funccommand': Command.dispatch_command('add_funccommand',
                        level=2000,
                        description='Add a command that uses a command'),
                    'alias': Command.dispatch_command('add_alias',
                        level=500,
                        description='Adds an alias to an already existing command',
                        examples=[
                            CommandExample(None, 'Add an alias to a command',
                                chat='user:!add alias test alsotest\n'
                                'bot>user:Successfully added the aliases alsotest to test',
                                description='Adds the alias !alsotest to the existing command !test').parse(),
                            CommandExample(None, 'Add multiple aliases to a command',
                                chat='user:!add alias test alsotest newtest test123\n'
                                'bot>user:Successfully added the aliases alsotest, newtest, test123 to test',
                                description='Adds the aliases !alsotest, !newtest, and !test123 to the existing command !test').parse(),
                            ]),

                    })
        self.internal_commands['edit'] = Command.multiaction_command(
                level=100,
                delay_all=0,
                delay_user=0,
                default=None,
                command='edit',
                commands={
                    'command': Command.dispatch_command('edit_command',
                        level=500,
                        description='Edit an already-existing command',
                        examples=[
                            CommandExample(None, 'Change the response',
                                chat='user:!edit command test This is the new response!\n'
                                'bot>user:Updated the command (ID: 29)',
                                description='Changes the text response for the command !test to "This is the new response!"').parse(),
                            CommandExample(None, 'Change the Global Cooldown',
                                chat='user:!edit command test --cd 10\n'
                                'bot>user:Updated the command (ID: 29)',
                                description='Changes the global cooldown for the command !test to 10 seconds').parse(),
                            CommandExample(None, 'Change the User-specific Cooldown',
                                chat='user:!edit command test --usercd 30\n'
                                'bot>user:Updated the command (ID: 29)',
                                description='Changes the user-specific cooldown for the command !test to 30 seconds').parse(),
                            CommandExample(None, 'Change the Level for a command',
                                chat='user:!edit command test --level 500\n'
                                'bot>user:Updated the command (ID: 29)',
                                description='Changes the command level for !test to level 500').parse(),
                            CommandExample(None, 'Change the Cost for a command',
                                chat='user:!edit command $test1 --cost 50\n'
                                'bot>user:Updated the command (ID: 27)',
                                description='Changes the command cost for !$test1 to 50 points, you should always use a $ for a command that cost points.').parse(),
                            CommandExample(None, 'Change a command to Moderator only',
                                chat='user:!edit command test --modonly\n'
                                'bot>user:Updated the command (ID: 29)',
                                description='This command can only be used for user with level 100 and Moderator status or user over level 500').parse(),
                            CommandExample(None, 'Remove Moderator only from a command',
                                chat='user:!edit command test --no-modonly\n'
                                'bot>user:Updated the command (ID: 29)',
                                description='This command can be used for normal users again.').parse(),
                            ]),
                    'funccommand': Command.dispatch_command('edit_funccommand',
                        level=2000,
                        description='Add a command that uses a command'),
                    })
        self.internal_commands['remove'] = Command.multiaction_command(
                level=100,
                delay_all=0,
                delay_user=0,
                default=None,
                command='remove',
                commands={
                    'command': Command.dispatch_command('remove_command',
                        level=500,
                        description='Remove a command!',
                        examples=[
                            CommandExample(None, 'Remove a command',
                                chat='user:!remove command Keepo123\n'
                                'bot>user:Successfully removed command with id 27',
                                description='Removes a command with the trigger !Keepo123').parse(),
                            CommandExample(None, 'Remove a command with the given ID.',
                                chat='user:!remove command 28\n'
                                'bot>user:Successfully removed command with id 28',
                                description='Removes a command with id 28').parse(),
                            ]),
                    'win': Command.dispatch_command('remove_win',
                        level=500,
                        description='Remove a win to something!'),
                    'alias': Command.dispatch_command('remove_alias',
                        level=500,
                        description='Removes an alias to an already existing command',
                        examples=[
                            CommandExample(None, 'Remove two aliases',
                                chat='user:!remove alias KeepoKeepo Keepo2Keepo\n'
                                'bot>user:Successfully removed 2 aliases.',
                                description='Removes KeepoKeepo and Keepo2Keepo as aliases').parse(),
                            ]),
                    })
        self.internal_commands['rem'] = self.internal_commands['remove']
        self.internal_commands['del'] = self.internal_commands['remove']
        self.internal_commands['delete'] = self.internal_commands['remove']
        self.internal_commands['eval'] = Command.dispatch_command('eval',
                level=2000,
                description='Run a raw python command. Debug mode only')

        return self.internal_commands

    def create_command(self, alias_str, **options):
        aliases = alias_str.lower().replace('!', '').split('|')
        for alias in aliases:
            if alias in self.data:
                return self.data[alias], False, alias

        command = Command(command=alias_str, **options)
        command.data = CommandData(command.id, **options)
        self.add_db_command_aliases(command)
        with DBManager.create_session_scope(expire_on_commit=False) as db_session:
            db_session.add(command)
            db_session.add(command.data)
            db_session.commit()
            db_session.expunge(command)
            db_session.expunge(command.data)
        self.db_session.add(command.data)
        self.commit()

        self.rebuild()
        return command, True, ''

    def edit_command(self, command_to_edit, **options):
        command_to_edit.set(**options)
        command_to_edit.data.set(**options)
        DBManager.session_add_expunge(command_to_edit)
        self.commit()

    def remove_command_aliases(self, command):
        aliases = command.command.split('|')
        for alias in aliases:
            if alias in self.db_commands:
                del self.db_commands[alias]
            else:
                log.warning('For some reason, {0} was not in the list of commands when we removed it.'.format(alias))

    def remove_command(self, command):
        self.remove_command_aliases(command)

        with DBManager.create_session_scope() as db_session:
            self.db_session.expunge(command.data)
            db_session.delete(command.data)
            db_session.delete(command)

        self.rebuild()

    def add_db_command_aliases(self, command):
        aliases = command.command.split('|')
        for alias in aliases:
            self.db_commands[alias] = command

        return len(aliases)

    def load_db_commands(self, **options):
        """ This method is only meant to be run once.
        Any further updates to the db_commands dictionary will be done
        in other methods.

        """

        if len(self.db_commands) > 0:
            return self.db_commands

        query = self.db_session.query(Command)

        if options.get('load_examples', False) is True:
            query = query.options(joinedload(Command.examples))
        if options.get('enabled', True) is True:
            query = query.filter_by(enabled=True)

        for command in query:
            self.add_db_command_aliases(command)
            self.db_session.expunge(command)
            if command.data is None:
                log.info('Creating command data for {}'.format(command.command))
                command.data = CommandData(command.id)
            self.db_session.add(command.data)

        return self.db_commands

    def rebuild(self):
        """ Rebuild the internal commands list from all sources.

        """

        def merge_commands(in_dict, out):
            for alias, command in in_dict.items():
                if command.action:
                    # Resets any previous modifications to the action.
                    # Right now, the only thing this resets is the MultiAction
                    # command list.
                    command.action.reset()

                if alias in out:
                    if (command.action and command.action.type == 'multi' and
                            out[alias].action and out[alias].action.type == 'multi'):
                        out[alias].action += command.action
                    else:
                        out[alias] = command
                else:
                    out[alias] = command

        self.data = {}
        db_commands = {alias: command for alias, command in self.db_commands.items() if command.enabled is True}

        merge_commands(self.internal_commands, self.data)
        merge_commands(db_commands, self.data)

        if self.module_manager is not None:
            for enabled_module in self.module_manager.modules:
                merge_commands(enabled_module.commands, self.data)

    def load(self, **options):
        self.load_internal_commands(**options)
        self.load_db_commands(**options)

        self.rebuild()

        return self

    def load_by_id(self, command_id):
        self.db_session.commit()
        command = self.db_session.query(Command).filter_by(id=command_id, enabled=True).one_or_none()
        if command:
            self.add_db_command_aliases(command)
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
        parser.add_argument('--subonly', dest='sub_only', action='store_true')
        parser.add_argument('--no-subonly', dest='sub_only', action='store_false')

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

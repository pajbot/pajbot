import collections
import datetime
import logging

import pajbot.models
from pajbot.modules import BaseModule
from pajbot.modules import ModuleType
from pajbot.modules.basic import BasicCommandsModule

log = logging.getLogger(__name__)


class DebugModule(BaseModule):

    ID = __name__.split('.')[-1]
    NAME = '!debug'
    DESCRIPTION = 'Debug commands and users'
    CATEGORY = 'Feature'
    ENABLED_DEFAULT = True
    MODULE_TYPE = ModuleType.TYPE_ALWAYS_ENABLED
    PARENT_MODULE = BasicCommandsModule

    def debug_command(self, **options):
        message = options['message']
        bot = options['bot']
        source = options['source']

        if message and len(message) > 0:
            try:
                id = int(message)
            except Exception:
                id = -1

            command = False

            if id == -1:
                potential_cmd = ''.join(message.split(' ')[:1]).lower()
                if potential_cmd in bot.commands:
                    command = bot.commands[potential_cmd]
            else:
                for key, potential_cmd in bot.commands.items():
                    if potential_cmd.id == id:
                        command = potential_cmd
                        break

            if not command:
                bot.whisper(source.username, 'No command found with the given parameters.')
                return False

            data = collections.OrderedDict()
            data['id'] = command.id
            data['level'] = command.level
            data['type'] = command.action.type if command.action is not None else '???'
            data['cost'] = command.cost
            data['cd_all'] = command.delay_all
            data['cd_user'] = command.delay_user
            data['mod_only'] = command.mod_only

            if data['type'] == 'message':
                data['response'] = command.action.response
            elif data['type'] == 'func' or data['type'] == 'rawfunc':
                data['cb'] = command.action.cb.__name__

            bot.whisper(source.username, ', '.join(['%s=%s' % (key, value) for (key, value) in data.items()]))
        else:
            bot.whisper(source.username, 'Usage: !debug command (COMMAND_ID|COMMAND_ALIAS)')
            return False

    def debug_user(self, **options):
        message = options['message']
        bot = options['bot']
        source = options['source']

        if message and len(message) > 0:
            username = message.split(' ')[0].strip().lower()
            user = bot.users.find(username)

            if user is None:
                bot.whisper(source.username, 'No user with this username found.')
                return False

            data = collections.OrderedDict()
            data['id'] = user.id
            data['level'] = user.level
            data['num_lines'] = user.num_lines
            data['points'] = user.points
            data['last_seen'] = user.last_seen.strftime('%Y-%m-%d %H:%M:%S %Z')
            try:
                data['last_active'] = user.last_active.strftime('%Y-%m-%d %H:%M:%S %Z')
            except:
                pass
            data['ignored'] = user.ignored
            data['banned'] = user.banned
            data['tokens'] = user.tokens

            bot.whisper(source.username, ', '.join(['%s=%s' % (key, value) for (key, value) in data.items()]))
        else:
            bot.whisper(source.username, 'Usage: !debug user USERNAME')
            return False

    def debug_tags(self, **options):
        message = options['message']
        bot = options['bot']
        source = options['source']

        if message and len(message) > 0:
            username = message.split(' ')[0].strip().lower()
            user = bot.users.find(username)

            if user is None:
                bot.whisper(source.username, 'No user with this username found.')
                return False

            data = collections.OrderedDict()
            user_tags = user.get_tags()

            if len(user_tags) == 0:
                bot.whisper(source.username, 'This user does not have any tags')
            else:
                for tag in user_tags:
                    data[tag] = datetime.datetime.fromtimestamp(user_tags[tag]).strftime('%Y-%m-%d')

                bot.whisper(source.username, '{} have the following tags: '.format(user.username_raw) + ', '.join(['%s until %s' % (key, value) for (key, value) in data.items()]))
        else:
            bot.whisper(source.username, 'Usage: !debug user USERNAME')
            return False

    def load_commands(self, **options):
        self.commands['debug'] = pajbot.models.command.Command.multiaction_command(
                level=100,
                delay_all=0,
                delay_user=0,
                default=None,
                commands={
                    'command': pajbot.models.command.Command.raw_command(self.debug_command,
                        level=250,
                        description='Debug a command',
                        examples=[
                            pajbot.models.command.CommandExample(None, 'Debug a command',
                                chat='user:!debug command ping\n'
                                'bot>user: id=210, level=100, type=message, cost=0, cd_all=10, cd_user=30, mod_only=False, response=Snusbot has been online for $(tb:bot_uptime)',
                                description='').parse(),
                            ]),
                    'user': pajbot.models.command.Command.raw_command(self.debug_user,
                        level=250,
                        description='Debug a user',
                        examples=[
                            pajbot.models.command.CommandExample(None, 'Debug a user',
                                chat='user:!debug user snusbot\n'
                                'bot>user: id=123, level=100, num_lines=45, points=225,  last_seen=2016-04-05 17:56:23 CEST, last_active=2016-04-05 17:56:07 CEST, ignored=False, banned=False, tokens=0',
                                description='').parse(),
                            ]),
                    'tags': pajbot.models.command.Command.raw_command(self.debug_tags,
                        level=100,
                        delay_all=0,
                        delay_user=5,
                        description='Debug tags for a user',
                        examples=[
                            pajbot.models.command.CommandExample(None, 'Debug tags for a user',
                                chat='user:!debug tags pajbot\n'
                                'bot>user: pajbot have the following tags: pajlada_sub until 2016-04-28',
                                description='').parse(),
                            ])
                    })

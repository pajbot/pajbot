import collections
import logging

from pajbot.models.command import Command
from pajbot.modules import BaseModule
from pajbot.modules import ModuleType

log = logging.getLogger(__name__)


class DebugModule(BaseModule):

    ID = __name__.split('.')[-1]
    NAME = '!debug'
    DESCRIPTION = 'Debug commands and users'
    CATEGORY = 'Feature'
    ENABLED_DEFAULT = True
    MODULE_TYPE = ModuleType.TYPE_ALWAYS_ENABLED

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
            data['last_seen'] = user.last_seen
            data['last_active'] = user.last_active
            data['tokens'] = user.get_tokens()

            bot.whisper(source.username, ', '.join(['%s=%s' % (key, value) for (key, value) in data.items()]))
        else:
            bot.whisper(source.username, 'Usage: !debug user USERNAME')

    def load_commands(self, **options):
        self.commands['debug'] = Command.multiaction_command(
                level=250,
                delay_all=0,
                delay_user=0,
                default=None,
                commands={
                    'command': Command.raw_command(self.debug_command,
                        level=250,
                        description='Debug a command'),
                    'user': Command.raw_command(self.debug_user,
                        level=250,
                        description='Debug a user'),
                    })

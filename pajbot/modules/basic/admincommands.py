import logging

from pajbot.managers import AdminLogManager
from pajbot.models.command import Command
from pajbot.modules import BaseModule
from pajbot.modules import ModuleType
from pajbot.modules.basic import BasicCommandsModule

log = logging.getLogger(__name__)


class AdminCommandsModule(BaseModule):
    ID = __name__.split('.')[-1]
    NAME = 'Basic admin commands'
    DESCRIPTION = 'All miscellaneous admin commands'
    CATEGORY = 'Feature'
    ENABLED_DEFAULT = True
    MODULE_TYPE = ModuleType.TYPE_ALWAYS_ENABLED
    PARENT_MODULE = BasicCommandsModule

    def whisper(self, **options):
        message = options['message']
        bot = options['bot']

        if message:
            msg_args = message.split(' ')
            if len(msg_args) > 1:
                username = msg_args[0]
                rest = ' '.join(msg_args[1:])
                bot.whisper(username, rest)

    def level(self, **options):
        message = options['message']
        bot = options['bot']
        source = options['source']

        if message:
            msg_args = message.split(' ')
            if len(msg_args) > 1:
                username = msg_args[0].lower()
                new_level = int(msg_args[1])
                if new_level >= source.level:
                    bot.whisper(source.username, 'You cannot promote someone to the same or higher level as you ({0}).'.format(source.level))
                    return False

                # We create the user if the user didn't already exist in the database.
                user = bot.users[username]

                old_level = user.level
                user.level = new_level

                log_msg = '{}\'s user level changed from {} to {}'.format(
                        user.username_raw,
                        old_level,
                        new_level)

                bot.whisper(source.username, log_msg)

                AdminLogManager.add_entry('Userlevel edited', source, log_msg)

                return True

        bot.whisper(source.username, 'Usage: !level USERNAME NEW_LEVEL')
        return False

    def load_commands(self, **options):
        self.commands['w'] = Command.raw_command(self.whisper,
                level=2000,
                description='Send a whisper from the bot')
        self.commands['level'] = Command.raw_command(self.level,
                level=1000,
                description='Set a users level')

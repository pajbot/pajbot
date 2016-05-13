import logging

from pajbot.managers import AdminLogManager
from pajbot.models.command import Command
from pajbot.models.command import CommandExample
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

    def edit_points(self, **options):
        message = options['message']
        bot = options['bot']
        source = options['source']

        if message:
            msg_split = message.split(' ')
            if len(msg_split) < 2:
                # The user did not supply enough arguments
                bot.whisper(source.username, 'Usage: !editpoints USERNAME POINTS')
                return False

            username = msg_split[0]
            if len(username) < 2:
                # The username specified was too short. ;-)
                return False

            try:
                num_points = int(msg_split[1])
            except (ValueError, TypeError):
                # The user did not specify a valid integer for points
                bot.whisper(source.username, 'Invalid amount of points. Usage: !{command_name} USERNAME POINTS'.format(command_name=self.command_name))
                return False

            with bot.users.find_context(username) as user:
                if not user:
                    bot.whisper(source.username, 'This user does not exist FailFish')
                    return False

                user.points += num_points

                if num_points >= 0:
                    bot.whisper(source.username, 'Successfully gave {} {} points.'.format(user.username_raw, num_points))
                else:
                    bot.whisper(source.username, 'Successfully removed {} points from {}.'.format(abs(num_points), user.username_raw))

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
                with bot.users.get_user_context(username) as user:
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
        self.commands['editpoints'] = Command.raw_command(self.edit_points,
                level=1500,
                description='Modifies a users points',
                examples=[
                    CommandExample(None, 'Give a user points',
                        chat='user:!editpoints pajlada 500\n'
                        'bot>user:Successfully gave pajlada 500 points.',
                        description='This creates 500 points and gives them to pajlada').parse(),
                    CommandExample(None, 'Remove points from a user',
                        chat='user:!editpoints pajlada -500\n'
                        'bot>user:Successfully removed 500 points from pajlada.',
                        description='This removes 500 points from pajlada. Users can go into negative points with this.').parse(),
                    ])
        self.commands['level'] = Command.raw_command(self.level,
                level=1000,
                description='Set a users level')

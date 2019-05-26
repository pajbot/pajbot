import logging

import pajbot.models
from pajbot.modules import BaseModule
from pajbot.modules import ModuleSetting

log = logging.getLogger(__name__)


class GivePointsModule(BaseModule):

    ID = __name__.split('.')[-1]
    NAME = 'Give Points'
    DESCRIPTION = 'Allows users to donate points to others'
    CATEGORY = 'Feature'
    SETTINGS = [
            ModuleSetting(
                key='command_name',
                label='Command name (i.e. givepoints)',
                type='text',
                required=True,
                placeholder='Command name (no !)',
                default='givepoints',
                constraints={
                    'min_str_len': 2,
                    'max_str_len': 25,
                    }),
            ModuleSetting(
                key='source_requires_sub',
                label='Users need to be subbed to give away points',
                type='boolean',
                required=True,
                default=True),
            ModuleSetting(
                key='target_requires_sub',
                label='Target needs to be subbed to receive points',
                type='boolean',
                required=True,
                default=False)
            ]

    def give_points(self, **options):
        bot = options['bot']
        source = options['source']
        message = options['message']

        if message is None or len(message) == 0:
            # The user did not supply any arguments
            return False

        msg_split = message.split(' ')
        if len(msg_split) < 2:
            # The user did not supply enough arguments
            bot.whisper(source.username, 'Usage: !{command_name} USERNAME POINTS'.format(command_name=self.command_name))
            return False

        username = msg_split[0]
        if len(username) < 2:
            # The username specified was too short. ;-)
            return False

        if msg_split[1].lower() == 'all':
            num_points = source.points_available()
        else:
            try:
                num_points = int(msg_split[1])
            except (ValueError, TypeError):
                # The user did not specify a valid integer for points
                bot.whisper(source.username, 'Invalid amount of points. Usage: !{command_name} USERNAME POINTS'.format(command_name=self.command_name))
                return False

        if num_points <= 0:
            # The user tried to specify a negative amount of points
            bot.whisper(source.username, 'You cannot give away negative points OMGScoots')
            return True

        if not source.can_afford(num_points):
            # The user tried giving away more points than he owns
            bot.whisper(source.username, 'You cannot give away more points than you have. You have {} points.'.format(source.points))
            return False

        with bot.users.find_context(username) as target:
            if target is None:
                # The user tried donating points to someone who doesn't exist in our database
                bot.whisper(source.username, 'This user does not exist FailFish')
                return False

            if target == source:
                # The user tried giving points to themselves
                bot.whisper(source.username, 'You can\'t give points to yourself OMGScoots')
                return True

            if self.settings['target_requires_sub'] is True and target.subscriber is False:
                # Settings indicate that the target must be a subscriber, which he isn't
                bot.whisper(source.username, 'Your target must be a subscriber.')
                return False

            source.points -= num_points
            target.points += num_points

            bot.whisper(source.username, 'Successfully gave away {num_points} points to {target.username_raw}'.format(num_points=num_points, target=target))
            bot.whisper(target.username, '{source.username_raw} just gave you {num_points} points! You should probably thank them ;-)'.format(num_points=num_points, source=source))

    def load_commands(self, **options):
        self.command_name = self.settings['command_name'].lower().replace('!', '').replace(' ', '')
        self.commands[self.command_name] = pajbot.models.command.Command.raw_command(
                self.give_points,
                sub_only=self.settings['source_requires_sub'],
                delay_all=0,
                delay_user=60,
                can_execute_with_whisper=True,
                examples=[
                    pajbot.models.command.CommandExample(None, 'Give points to a user.',
                        chat='user:!{0} pajapaja 4444\n'
                        'bot>user: Successfully gave away 4444 points to pajapaja'.format(self.command_name),
                        description='').parse(),
                    ])

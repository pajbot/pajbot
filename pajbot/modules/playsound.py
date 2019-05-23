import logging
from typing import Optional

import json

from argparse import ArgumentParser

import re

from pajbot.managers.db import DBManager
from pajbot.models.playsound import Playsound
from pajbot.modules import BaseModule
from pajbot.modules import ModuleSetting

log = logging.getLogger(__name__)


class PlaysoundModule(BaseModule):
    ID = __name__.split('.')[-1]
    NAME = 'Playsound'
    DESCRIPTION = 'Play a sound on stream with !#playsound'
    CATEGORY = 'Feature'
    SETTINGS = [
        ModuleSetting(
            key='point_cost',
            label='Point cost',
            type='number',
            required=True,
            placeholder='Point cost',
            default=200,
            constraints={
                'min_value': 0,
                'max_value': 999999,
            }),
        ModuleSetting(
            key='token_cost',
            label='Token cost',
            type='number',
            required=True,
            placeholder='Token cost',
            default=0,
            constraints={
                'min_value': 0,
                'max_value': 15,
            }),
        ModuleSetting(
            key='global_cd',
            label='Global playsound cooldown (seconds)',
            type='number',
            required=True,
            placeholder='',
            default=2,
            constraints={
                'min_value': 0,
                'max_value': 600,
            }),
        ModuleSetting(
            key='default_sample_cd',
            label='Default per-sample cooldown (seconds)',
            type='number',
            required=True,
            placeholder='',
            default=30,
            constraints={
                'min_value': 0,
                'max_value': 600,
            }),
        ModuleSetting(
            key='global_volume',
            label='Global volume (0-100)',
            type='number',
            required=True,
            placeholder='',
            default=100,
            constraints={
                'min_value': 0,
                'max_value': 100,
            }),
        ModuleSetting(
            key='sub_only',
            label='Subscribers only',
            type='boolean',
            required=True,
            default=False),
        ModuleSetting(
            key='can_whisper',
            label='Command can be whispered',
            type='boolean',
            required=True,
            default=True),
    ]

    def __init__(self, bot):
        super().__init__(bot)

        # this is for the "Test on stream" button on the admin page
        if bot:
            bot.socket_manager.add_handler('playsound.play', self.on_web_playsound)

        self.sample_cooldown = []

    # when a "Test on stream" is triggered via the Web UI.
    def on_web_playsound(self, data, conn):
        # on playsound test triggered by the Web UI
        # this works even if the module is not enabled.
        playsound_name = data["name"]

        with DBManager.create_session_scope() as session:
            playsound = session.query(Playsound).filter(Playsound.name == playsound_name).one_or_none()

            if playsound is None:
                log.warning("Web UI tried to play invalid playsound. Ignoring.")
                return

            playsound.volume = int(round(playsound.volume * self.settings['global_volume'] / 100))

            payload = {
                "link": playsound.link,
                "volume": playsound.volume
            }

            log.debug("Playsound module is emitting payload: {}".format(json.dumps(payload)))
            self.bot.websocket_manager.emit('play_sound', payload)

    def play_sound(self, **options):
        bot = options['bot']
        message = options['message']
        source = options['source']

        if not message:
            return

        playsound_name = message.split(' ')[0].lower()

        if playsound_name in self.sample_cooldown:
            bot.whisper(source.username,
                        'The playsound {0} was played too recently. Please wait before trying to use it again'.format(
                            playsound_name))
            return False

        with DBManager.create_session_scope() as session:
            # load playsound from the database
            playsound: Optional[Playsound] = session.query(Playsound).filter(
                Playsound.name == playsound_name).one_or_none()

            if playsound is None:
                # TODO link
                bot.whisper(source.username,
                            'The playsound you gave does not exist. Check out all the valid playsounds here: TODO link')
                return False

            if not playsound.enabled:
                # TODO link
                bot.whisper(source.username,
                            'The playsound you gave is disabled. Check out all the valid playsounds here: TODO link')
                return False

            if playsound.cooldown is None:
                playsound.cooldown = self.settings['default_sample_cd']

            playsound.volume = int(round(playsound.volume * self.settings['global_volume'] / 100))

            payload = {
                "link": playsound.link,
                "volume": playsound.volume
            }

            log.debug("Playsound module is emitting payload: {}".format(json.dumps(payload)))
            bot.websocket_manager.emit('play_sound', payload)

            self.sample_cooldown.append(playsound.name)
            bot.execute_delayed(playsound.cooldown, self.sample_cooldown.remove, (playsound.name,))

    def parse_playsound_arguments(self, message):
        """
        Available options:
        --volume VOLUME
        --cooldown COOLDOWN
        --enabled/--disabled
        """
        parser = ArgumentParser()
        parser.add_argument('--volume', dest='volume', type=int)
        # we parse this manually so we can allow "none" and things like that to unset the cooldown
        parser.add_argument('--cooldown', dest='cooldown', type=str)
        parser.add_argument('--enabled', dest='enabled', action='store_true')
        parser.add_argument('--disabled', dest='enabled', action='store_false')
        parser.set_defaults(volume=None, cooldown=None, enabled=None)

        try:
            args, unknown = parser.parse_known_args(message.split())
        except SystemExit:
            return False, False, False
        except:
            log.exception('Unhandled exception in add_command')
            return False, False, False

        # Strip options of any values that are set as None
        options = {k: v for k, v in vars(args).items() if v is not None}
        if len(unknown) < 1:
            # no name
            return False, False, False

        name = unknown[0]
        link = None if len(unknown) < 2 else ' '.join(unknown[1:])

        return options, name, link

    @staticmethod
    def validate_name(name):
        return name is not None

    re_valid_links = re.compile("^https://\\S*$")

    @staticmethod
    def validate_link(link):
        return link is not None and PlaysoundModule.re_valid_links.match(link)

    def update_link(self, bot, source, playsound, link):
        if link is not None:
            if not self.validate_link(link):
                bot.whisper(source.username, "Error: Invalid link. Valid links must start with https:// "
                                             "and cannot contain spaces")
                return False
            playsound.link = link
        return True

    @staticmethod
    def validate_volume(volume):
        return volume is not None and 0 <= volume <= 100

    def update_volume(self, bot, source, playsound, parsed_options):
        if 'volume' in parsed_options:
            if not self.validate_volume(parsed_options['volume']):
                bot.whisper(source.username, 'Error: Volume must be between 0 and 100.')
                return False
            playsound.volume = parsed_options['volume']
        return True

    @staticmethod
    def validate_cooldown(cooldown):
        return cooldown is None or cooldown >= 0

    def update_cooldown(self, bot, source, playsound, parsed_options):
        if 'cooldown' in parsed_options:
            if parsed_options['cooldown'].lower() == 'none':
                cooldown_int = None
            else:
                try:
                    cooldown_int = int(parsed_options['cooldown'])
                except ValueError:
                    bot.whisper(source.username, 'Error: Cooldown must be a number or the string "none".')
                    return False

            if not self.validate_cooldown(cooldown_int):
                bot.whisper(source.username, 'Error: Cooldown must be positive.')
                return False

            playsound.cooldown = cooldown_int
        return True

    def update_enabled(self, bot, source, playsound, parsed_options):
        if 'enabled' in parsed_options:
            playsound.enabled = parsed_options['enabled']
        return True

    def add_playsound_command(self, **options):
        """Method for creating playsounds.
        Usage: !add playsound PLAYSOUNDNAME LINK [options]
        Multiple options available:
        --volume VOLUME
        --cooldown COOLDOWN
        --enabled/--disabled
        """
        bot = options['bot']
        message = options['message']
        source = options['source']

        options, name, link = self.parse_playsound_arguments(message)

        # the parser does not enforce a link being present because the edit function
        # doesn't require it strictly, so apart from "False" link is being checked
        # for being None here.
        if options is False or name is False or link is False or link is None:
            bot.whisper(source.username, 'Invalid usage. Correct syntax: !add playsound <name> <link> ' +
                        '[--volume 0-100] [--cooldown 60/none] [--enabled/--disabled]')
            return

        with DBManager.create_session_scope() as session:
            count = session.query(Playsound).filter(Playsound.name == name).count()
            if count > 0:
                bot.whisper(source.username, 'A Playsound with that name already exists. Use !edit playsound ' +
                            'or !remove playsound to edit or delete it.')
                return

            playsound = Playsound(name=name)

            if not self.update_link(bot, source, playsound, link):
                return

            if not self.update_volume(bot, source, playsound, options):
                return

            if not self.update_cooldown(bot, source, playsound, options):
                return

            if not self.update_enabled(bot, source, playsound, options):
                return

            session.add(playsound)
            bot.whisper(source.username, 'Successfully added your playsound.')

    def edit_playsound_command(self, **options):
        """Method for editing playsounds.
        Usage: !edit playsound PLAYSOUNDNAME [LINK] [options]
        Multiple options available:
        --volume VOLUME
        --cooldown COOLDOWN
        --enabled/--disabled
        """
        bot = options['bot']
        message = options['message']
        source = options['source']

        options, name, link = self.parse_playsound_arguments(message)

        if options is False or name is False or link is False:
            bot.whisper(source.username, 'Invalid usage. Correct syntax: !edit playsound <name> [link] ' +
                        '[--volume 0-100] [--cooldown 60/none] [--enabled/--disabled]')
            return

        with DBManager.create_session_scope() as session:
            playsound = session.query(Playsound).filter(Playsound.name == name).one_or_none()
            if playsound is None:
                bot.whisper(source.username, 'No playsound with that name exists. You can create playsounds with '
                                             '!add playsound <name> <link> [options].')
                return

            if not self.update_link(bot, source, playsound, link):
                return

            if not self.update_volume(bot, source, playsound, options):
                return

            if not self.update_cooldown(bot, source, playsound, options):
                return

            if not self.update_enabled(bot, source, playsound, options):
                return

            session.add(playsound)
            bot.whisper(source.username, 'Successfully edited your playsound.')

    def remove_playsound_command(self, **options):
        """Method for removing playsounds.
        Usage: !edit playsound PLAYSOUNDNAME
        """
        bot = options['bot']
        message = options['message']
        source = options['source']

        split = message.split(' ', 1)
        # check for empty string
        if not split[0]:
            bot.whisper(source.username, 'Invalid usage. Correct syntax: !remove playsound <name>')
            return

        playsound_name = split[0]

        with DBManager.create_session_scope() as session:
            playsound = session.query(Playsound).filter(Playsound.name == playsound_name).one_or_none()

            if playsound is None:
                bot.whisper(source.username, 'No playsound with that name exists.')
                return

            session.delete(playsound)
            bot.whisper(source.username, 'Successfully deleted your playsound.')

    def load_commands(self, **options):
        from pajbot.models.command import Command
        from pajbot.models.command import CommandExample

        self.commands['#playsound'] = Command.raw_command(
            self.play_sound,
            tokens_cost=self.settings['token_cost'],
            cost=self.settings['point_cost'],
            sub_only=self.settings['sub_only'],
            delay_all=self.settings['global_cd'],
            description='Play a sound on stream!',
            can_execute_with_whisper=self.settings['can_whisper'],
            examples=[
                CommandExample(None, 'Play the "cumming" sample',
                               chat='user:!#playsound cumming\n'
                                    'bot>user:Successfully played your sample cumming').parse(),
                CommandExample(None, 'Play the "fuckyou" sample',
                               chat='user:!#playsound fuckyou\n'
                                    'bot>user:Successfully played your sample fuckyou').parse(),
            ],
        )

        self.commands['#playsound'].long_description = 'Playsounds can be tried out <a href="/playsounds">here</a>'

        self.commands['add'] = Command.multiaction_command(
            level=100,
            delay_all=0,
            delay_user=0,
            default=None,
            command='add',
            commands={
                'playsound': Command.raw_command(
                    self.add_playsound_command,
                    level=500,
                    delay_all=0,
                    delay_user=0,
                    description='Creates a new playsound',
                    examples=[
                        CommandExample(
                            None, 'Create a new playsound',
                            chat='user:!add playsound doot https://i.nuuls.com/Bb4aX.mp3\n'
                                 'bot>user:Successfully created your playsound',
                            description='Creates the "doot" playsound with the given link.').parse(),
                        CommandExample(
                            None, 'Create a new playsound and sets volume',
                            chat='user:!add playsound doot https://i.nuuls.com/Bb4aX.mp3 --volume 50\n'
                                 'bot>user:Successfully created your playsound',
                            description='Creates the "doot" playsound with the given link and 50% volume.').parse(),
                        CommandExample(
                            None, 'Create a new playsound and sets cooldown',
                            chat='user:!add playsound doot https://i.nuuls.com/Bb4aX.mp3 --cooldown 60\n'
                                 'bot>user:Successfully created your playsound',
                            description='Creates the "doot" playsound with the given link and 1 minute cooldown.').parse(),
                        CommandExample(
                            None, 'Create a new playsound and disable it',
                            chat='user:!add playsound doot https://i.nuuls.com/Bb4aX.mp3 --disabled\n'
                                 'bot>user:Successfully created your playsound',
                            description='Creates the "doot" playsound with the given link and initially disables it.').parse(),
                    ]),
            }
        )

        self.commands['edit'] = Command.multiaction_command(
            level=100,
            delay_all=0,
            delay_user=0,
            default=None,
            command='edit',
            commands={
                'playsound': Command.raw_command(
                    self.edit_playsound_command,
                    level=500,
                    delay_all=0,
                    delay_user=0,
                    description='Edits an existing playsound',
                    examples=[
                        CommandExample(
                            None, 'Edit an existing playsound\'s link',
                            chat='user:!edit playsound doot https://i.nuuls.com/Bb4aX.mp3\n'
                                 'bot>user:Successfully edited your playsound',
                            description='Updates the link of the "doot" playsound.').parse(),
                        CommandExample(
                            None, 'Edit an existing playsound\'s volume',
                            chat='user:!edit playsound doot --volume 50\n'
                                 'bot>user:Successfully edited your playsound',
                            description='Updates the volume of the "doot" playsound to 50%.').parse(),
                        CommandExample(
                            None, 'Edit an existing playsound\'s cooldown',
                            chat='user:!edit playsound doot --cooldown 60\n'
                                 'bot>user:Successfully edited your playsound',
                            description='Updates the cooldown of the "doot" playsound to 1 minute.').parse(),
                        CommandExample(
                            None, 'Disable an existing playsound',
                            chat='user:!edit playsound doot --disabled\n'
                                 'bot>user:Successfully edited your playsound',
                            description='Disables the "doot" playsound.').parse(),
                        CommandExample(
                            None, 'Enable an existing playsound',
                            chat='user:!edit playsound doot --enabled\n'
                                 'bot>user:Successfully edited your playsound',
                            description='Enables the "doot" playsound.').parse(),
                    ]),
            }
        )

        self.commands['remove'] = Command.multiaction_command(
            level=100,
            delay_all=0,
            delay_user=0,
            default=None,
            command='remove',
            commands={
                'playsound': Command.raw_command(
                    self.remove_playsound_command,
                    level=500,
                    delay_all=0,
                    delay_user=0,
                    description='Removes an existing playsound',
                    examples=[
                        CommandExample(
                            None, 'Remove an existing playsound',
                            chat='user:!remove playsound doot\n'
                                 'bot>user:Successfully removed your playsound',
                            description='Removes the "doot" playsound.').parse(),
                    ]),
            }
        )

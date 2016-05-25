import logging

import pajbot.models
from pajbot.modules import BaseModule
from pajbot.modules import ModuleSetting

log = logging.getLogger(__name__)


class HighlightModule(BaseModule):
    ID = __name__.split('.')[-1]
    NAME = 'Highlight'
    DESCRIPTION = 'Gives users the ability to create highlights that happen on the stream'
    ENABLED_DEFAULT = False
    CATEGORY = 'Feature'
    SETTINGS = [
            ModuleSetting(
                key='allow_subs',
                label='Allow subs to use !add highlight',
                type='boolean',
                required=True,
                default=False)
            ]

    def is_message_bad(self, source, msg_raw, event):
        msg_lower = msg_raw.lower()

        res = self.bot.banphrase_manager.check_message(msg_raw, source)
        if res is not False:
            self.bot.banphrase_manager.punish(source, res)
            return True

        for f in self.bot.filters:
            if f.type == 'regex':
                m = f.search(source, msg_lower)
                if m:
                    log.debug('Matched regex filter \'{0}\''.format(f.name))
                    f.run(self.bot, source, msg_raw, event, {'match': m})
                    return True
            elif f.type == 'banphrase':
                if f.filter in msg_lower:
                    log.debug('Matched banphrase filter \'{0}\''.format(f.name))
                    f.run(self.bot, source, msg_raw, event)
                    return True

        return False  # message was ok

    def enable(self, bot):
        self.bot = bot

    def add_highlight(self, **options):
        """Method for creating highlights
        Usage: !add highlight [options] DESCRIPTION
        Options available:
        --offset SECONDS
        """

        message = options['message']
        bot = options['bot']
        source = options['source']

        # Failsafe in case the user does not send a message
        message = message if message else ''

        options, description = bot.stream_manager.parse_highlight_arguments(message)

        if options is False:
            bot.whisper(source.username, 'Invalid highlight arguments.')
            return False

        options['created_by'] = source.id

        if len(description) > 0:
            options['description'] = description

        if 'id' in options:
            bot.whisper(source.username, 'Use !edit highlight to edit the highlight instead.')
            return False
        else:
            res = bot.stream_manager.create_highlight(**options)

            if res is True:
                bot.whisper(source.username, 'Successfully created your highlight')
            else:
                bot.whisper(source.username, 'An error occured while adding your highlight: {0}'.format(res))

            log.info('Create a highlight at the current timestamp!')

    def edit_highlight(self, **options):
        """Method for editing highlights
        Usage: !edit highlight [options] DESCRIPTION
        """

        message = options['message']
        bot = options['bot']
        source = options['source']

        # Failsafe in case the user does not send a message
        message = message if message else ''

        options, description = bot.stream_manager.parse_highlight_arguments(message)

        if options is False:
            bot.whisper(source.username, 'Invalid highlight arguments.')
            return False

        options['last_edited_by'] = source.id

        if len(description) > 0:
            options['description'] = description

        if 'id' in options:
            id = options['id']
            del options['id']
            if len(options) > 0:
                res = bot.stream_manager.update_highlight(id, **options)

                if res is True:
                    bot.whisper(source.username, 'Successfully updated your highlight ({0})'.format(', '.join([key for key in options])))
                else:
                    bot.whisper(source.username, 'A highlight with this ID does not exist, or something went terribly wrong (if this response is super late). Contact pajlada')
            else:
                bot.whisper(source.username, 'Nothing to update! Give me some arguments')
        else:
            bot.whisper(source.username, 'Missing --id for which highlight to edit. Did you mean to create a new highlight? In that case, use !add highlight instead!')

    def remove_highlight(self, **options):
        """Dispatch method for removing highlights
        Usage: !remove highlight HIGHLIGHT_ID
        """

        message = options['message']
        bot = options['bot']
        source = options['source']

        if message is None:
            bot.whisper(source.username, 'Usage: !remove highlight ID')
            return False

        try:
            id = int(message.split()[0])
        except ValueError:
            bot.whisper(source.username, 'Usage: !remove highlight ID')
            return False

        res = bot.stream_manager.remove_highlight(id)
        if res is True:
            bot.whisper(source.username, 'Successfully removed highlight with ID {}.'.format(id))
        else:
            bot.whisper(source.username, 'No highlight with the ID {} found.'.format(id))

    def load_commands(self, **options):
        try:
            level_trusted_mods = 100 if self.bot.trusted_mods else 500
            mod_only_trusted_mods = True if self.bot.trusted_mods else False
        except AttributeError:
            level_trusted_mods = 500
            mod_only_trusted_mods = False

        if self.settings['allow_subs']:
            add_highlight_level = 100
            mod_only_trusted_mods = False
        else:
            add_highlight_level = level_trusted_mods

        self.commands['add'] = pajbot.models.command.Command.multiaction_command(
                level=100,
                delay_all=0,
                delay_user=0,
                default=None,
                command='add',
                commands={
                    'highlight': pajbot.models.command.Command.raw_command(self.add_highlight,
                        level=add_highlight_level,
                        delay_all=30 if self.settings['allow_subs'] else 0,
                        delay_user=60 if self.settings['allow_subs'] else 4,
                        mod_only=mod_only_trusted_mods,
                        sub_only=self.settings['allow_subs'],
                        description='Creates a highlight at the current timestamp',
                        examples=[
                            pajbot.models.command.CommandExample(None, 'Create a highlight',
                                chat='user:!add highlight 1v5 Pentakill\n'
                                'bot>user:Successfully created your highlight',
                                description='Creates a highlight with the description 1v5 Pentakill').parse(),
                            pajbot.models.command.CommandExample(None, 'Create a highlight with a different offset',
                                chat='user:!add highlight 1v5 Pentakill --offset 60\n'
                                'bot>user:Successfully created your highlight',
                                description='Creates a highlight with the description 1v5 Pentakill and an offset of 60 seconds.').parse(),
                            ]),
                        }
                )

        self.commands['edit'] = pajbot.models.command.Command.multiaction_command(
                level=100,
                delay_all=0,
                delay_user=0,
                default=None,
                command='edit',
                commands={
                    'highlight': pajbot.models.command.Command.raw_command(self.edit_highlight,
                        level=level_trusted_mods,
                        mod_only=mod_only_trusted_mods,
                        description='Edit the highlight with the given ID',
                        examples=[
                            pajbot.models.command.CommandExample(None, 'Change the offset with the given ID.',
                                chat='user:!edit highlight --offset 180 --id 12\n'
                                'bot>user:Successfully updated your highlight (offset)',
                                description='Changes the offset to 180 seconds for the highlight ID 12').parse(),
                            pajbot.models.command.CommandExample(None, 'Change the description with the given ID.',
                                chat='user:!edit highlight 1v5 Pentakill PogChamp VAC --id 12\n'
                                'bot>user:Successfully updated your highlight (description)',
                                description='Changes the description to \'1v5 Pentakill PogChamp VAC\' for highlight ID 12.').parse(),
                            pajbot.models.command.CommandExample(None, 'Change the VOD link to a mirror link.',
                                chat='user:!edit highlight --id 12 --link http://www.twitch.tv/imaqtpie/v/27878606\n'  # TODO turn off autolink
                                'bot>user:Successfully updated your highlight (override_link)',
                                description='Changes the link for highlight ID 12 to http://www.twitch.tv/imaqtpie/v/27878606').parse(),
                            pajbot.models.command.CommandExample(None, 'Change the mirror link back to the VOD link.',
                                chat='user:!edit highlight --id 12 --no-link\n'
                                'bot>user:Successfully updated your highlight (override_link)',
                                description='Changes the link for highlight ID 12 back to the twitch VOD link.').parse(),
                            ]),
                    }
                )

        self.commands['remove'] = pajbot.models.command.Command.multiaction_command(
                level=100,
                delay_all=0,
                delay_user=0,
                default=None,
                command='remove',
                commands={
                    'highlight': pajbot.models.command.Command.raw_command(self.remove_highlight,
                        level=level_trusted_mods,
                        mod_only=mod_only_trusted_mods,
                        description='Removes a highlight with the given ID.',
                        examples=[
                            pajbot.models.command.CommandExample(None, 'Remove a highlight',
                                chat='user:!remove highlight 2\n'
                                'bot>user:Successfully removed highlight with ID 2.',
                                description='Removes the highlight ID 2').parse(),
                            ]),
                    }
                )

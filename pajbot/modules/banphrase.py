import logging

from pajbot.managers import AdminLogManager
from pajbot.managers import DBManager
from pajbot.models.command import Command
from pajbot.models.command import CommandExample
from pajbot.models.handler import HandlerManager
from pajbot.modules import BaseModule

log = logging.getLogger(__name__)


class BanphraseModule(BaseModule):

    ID = __name__.split('.')[-1]
    NAME = 'Banphrase'
    DESCRIPTION = 'Looks at each message for banned phrases, and takes actions accordingly'
    ENABLED_DEFAULT = True
    CATEGORY = 'Filter'
    SETTINGS = []

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
        HandlerManager.add_handler('on_message', self.on_message, priority=150)

    def disable(self, bot):
        HandlerManager.remove_handler('on_message', self.on_message)

    def on_message(self, source, message, emotes, whisper, urls, event):
        if whisper:
            return
        if source.level >= 500 or source.moderator:
            return

        if self.is_message_bad(source, message, event):
            # we matched a filter.
            # return False so no more code is run for this message
            return False

    def add_banphrase(self, **options):
        """Method for creating and editing banphrases.
        Usage: !add banphrase BANPHRASE [options]
        Multiple options available:
        --length LENGTH
        --perma/--no-perma
        --notify/--no-notify
        """

        message = options['message']
        bot = options['bot']
        source = options['source']

        if message:
            options, phrase = bot.banphrase_manager.parse_banphrase_arguments(message)

            if options is False:
                bot.whisper(source.username, 'Invalid banphrase')
                return False

            options['added_by'] = source.id
            options['edited_by'] = source.id

            banphrase, new_banphrase = bot.banphrase_manager.create_banphrase(phrase, **options)

            if new_banphrase is True:
                bot.whisper(source.username, 'Added your banphrase (ID: {banphrase.id})'.format(banphrase=banphrase))
                AdminLogManager.post('Banphrase added', source, phrase)
                return True

            banphrase.set(**options)
            banphrase.data.set(edited_by=options['edited_by'])
            DBManager.session_add_expunge(banphrase)
            bot.banphrase_manager.commit()
            bot.whisper(source.username, 'Updated your banphrase (ID: {banphrase.id}) with ({what})'.format(banphrase=banphrase, what=', '.join([key for key in options if key != 'added_by'])))
            AdminLogManager.post('Banphrase edited', source, phrase)

    def remove_banphrase(self, **options):
        message = options['message']
        bot = options['bot']
        source = options['source']

        if message:
            id = None
            try:
                id = int(message)
            except ValueError:
                pass

            banphrase = bot.banphrase_manager.find_match(message=message, id=id)

            if banphrase is None:
                bot.whisper(source.username, 'No banphrase with the given parameters found')
                return False

            AdminLogManager.post('Banphrase removed', source, banphrase.phrase)
            bot.whisper(source.username, 'Successfully removed banphrase with id {0}'.format(banphrase.id))
            bot.banphrase_manager.remove_banphrase(banphrase)
        else:
            bot.whisper(source.username, 'Usage: !remove banphrase (BANPHRASE_ID)')
            return False

    def load_commands(self, **options):
        self.commands['add'] = Command.multiaction_command(
                level=100,
                delay_all=0,
                delay_user=0,
                default=None,
                command='add',
                commands={
                    'banphrase': Command.raw_command(self.add_banphrase,
                        level=500,
                        description='Add a banphrase!',
                        delay_all=0,
                        delay_user=0,
                        examples=[
                            CommandExample(None, 'Create a banphrase',
                                chat='user:!add banphrase testman123\n'
                                'bot>user:Inserted your banphrase (ID: 83)',
                                description='This creates a banphrase with the default settings. Whenever a non-moderator types testman123 in chat they will be timed out for 300 seconds and notified through a whisper that they said something they shouldn\'t have said').parse(),
                            CommandExample(None, 'Create a banphrase that permabans people',
                                chat='user:!add banphrase testman123 --perma\n'
                                'bot>user:Inserted your banphrase (ID: 83)',
                                description='This creates a banphrase that permabans the user who types testman123 in chat. The user will be notified through a whisper that they said something they shouldn\'t have said').parse(),
                            CommandExample(None, 'Create a banphrase that permabans people without a notification',
                                chat='user:!add banphrase testman123 --perma --no-notify\n'
                                'bot>user:Inserted your banphrase (ID: 83)',
                                description='This creates a banphrase that permabans the user who types testman123 in chat').parse(),
                            CommandExample(None, 'Change the default timeout length for a banphrase',
                                chat='user:!add banphrase testman123 --time 123\n'
                                'bot>user:Updated the given banphrase (ID: 83) with (time, extra_args)',
                                description='Changes the default timeout length to a custom time of 123 seconds').parse(),
                            CommandExample(None, 'Make it so a banphrase cannot be triggered by subs',
                                chat='user:!add banphrase testman123 --subimmunity\n'
                                'bot>user:Updated the given banphrase (ID: 83) with (sub_immunity)',
                                description='Changes a command so that the banphrase can only be triggered by people who are not subscribed to the channel.').parse(),
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
                    'banphrase': Command.raw_command(self.remove_banphrase,
                        level=500,
                        delay_all=0,
                        delay_user=0,
                        description='Remove a banphrase!',
                        examples=[
                            CommandExample(None, 'Remove a banphrase',
                                chat='user:!remove banphrase KeepoKeepo\n'
                                'bot>user:Successfully removed banphrase with id 33',
                                description='Removes a banphrase with the trigger KeepoKeepo.').parse(),
                            CommandExample(None, 'Remove a banphrase with the given ID.',
                                chat='user:!remove banphrase 25\n'
                                'bot>user:Successfully removed banphrase with id 25',
                                description='Removes a banphrase with id 25').parse(),
                            ]),
                    }
                )

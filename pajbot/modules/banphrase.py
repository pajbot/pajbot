from bs4 import BeautifulSoup
from pajbot.apiwrappers import SafeBrowsingAPI

from pajbot.modules import BaseModule, ModuleSetting
from pajbot.models.db import DBManager, Base
from pajbot.actions import ActionQueue, Action
from pajbot.models.command import Command, CommandExample
from pajbot.models.handler import HandlerManager

import re
import requests
import logging
import time
import urllib.parse
from sqlalchemy import Column, Integer, String
from sqlalchemy.dialects.mysql import TEXT

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
        HandlerManager.add_handler('on_message', self.on_message, priority=50)

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

    def load_commands(self, **options):
        self.commands['add'] = Command.multiaction_command(
                level=100,
                delay_all=0,
                delay_user=0,
                default=None,
                command='add',
                commands={
                    'banphrase': Command.dispatch_command('add_banphrase',
                        level=500,
                        description='Add a banphrase!',
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
                    'banphrase': Command.dispatch_command('remove_banphrase',
                        level=500,
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

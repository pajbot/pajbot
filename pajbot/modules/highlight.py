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


class HighlightModule(BaseModule):
    ID = __name__.split('.')[-1]
    NAME = 'Highlight'
    DESCRIPTION = 'Gives users the ability to create highlights that happen on the stream'
    ENABLED_DEFAULT = False
    CATEGORY = 'Feature'
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
        try:
            level_trusted_mods = 100 if self.bot.trusted_mods else 500
            mod_only_trusted_mods = True if self.bot.trusted_mods else False
        except AttributeError:
            level_trusted_mods = 500
            mod_only_trusted_mods = False

        self.commands['add'] = Command.multiaction_command(
                level=100,
                delay_all=0,
                delay_user=0,
                default=None,
                command='add',
                commands={
                    'highlight': Command.dispatch_command('add_highlight',
                        level=100,
                        mod_only=True,
                        description='Creates a highlight at the current timestamp',
                        examples=[
                            CommandExample(None, 'Create a highlight',
                                chat='user:!add highlight 1v5 Pentakill\n'
                                'bot>user:Successfully created your highlight',
                                description='Creates a highlight with the description 1v5 Pentakill').parse(),
                            CommandExample(None, 'Create a highlight with a different offset',
                                chat='user:!add highlight 1v5 Pentakill --offset 60\n'
                                'bot>user:Successfully created your highlight',
                                description='Creates a highlight with the description 1v5 Pentakill and an offset of 60 seconds.').parse(),
                            CommandExample(None, 'Change the offset with the given ID.',
                                chat='user:!add highlight --offset 180 --id 12\n'
                                'bot>user:Successfully updated your highlight (offset)',
                                description='Changes the offset to 180 seconds for the highlight ID 12').parse(),
                            CommandExample(None, 'Change the description with the given ID.',
                                chat='user:!add highlight 1v5 Pentakill PogChamp VAC --id 12\n'
                                'bot>user:Successfully updated your highlight (description)',
                                description='Changes the description to \'1v5 Pentakill PogChamp VAC\' for highlight ID 12.').parse(),
                            CommandExample(None, 'Change the VOD link to a mirror link.',
                                chat='user:!add highlight --id 12 --link http://www.twitch.tv/imaqtpie/v/27878606\n'  # TODO turn off autolink
                                'bot>user:Successfully updated your highlight (override_link)',
                                description='Changes the link for highlight ID 12 to http://www.twitch.tv/imaqtpie/v/27878606').parse(),
                            CommandExample(None, 'Change the mirror link back to the VOD link.',
                                chat='user:!add highlight --id 12 --no-link\n'
                                'bot>user:Successfully updated your highlight (override_link)',
                                description='Changes the link for highlight ID 12 back to the twitch VOD link.').parse(),
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
                    'highlight': Command.dispatch_command('remove_highlight',
                        level=level_trusted_mods,
                        mod_only=mod_only_trusted_mods,
                        description='Removes a highlight with the given ID.',
                        examples=[
                            CommandExample(None, 'Remove a highlight',
                                chat='user:!remove highlight 2\n'
                                'bot>user:Successfully removed highlight with ID 2.',
                                description='Removes the highlight ID 2').parse(),
                            ]),
                    }
                )

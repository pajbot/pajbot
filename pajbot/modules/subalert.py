import logging
import re

from pajbot.managers.handler import HandlerManager
from pajbot.managers.user import UserManager
from pajbot.modules import BaseModule
from pajbot.modules import ModuleSetting

log = logging.getLogger(__name__)


class SubAlertModule(BaseModule):

    ID = __name__.split('.')[-1]
    NAME = 'Subscription Alert (text)'
    DESCRIPTION = 'Prints a message in chat or a whisper for someone who subscribed'
    CATEGORY = 'Feature'
    ENABLED_DEFAULT = True
    SETTINGS = [
            ModuleSetting(
                key='chat_message',
                label='Enable a chat message for someone who subscribed',
                type='boolean',
                required=True,
                default=True),
            ModuleSetting(
                key='new_sub',
                label='New sub chat message | Available arguments: {username}',
                type='text',
                required=True,
                placeholder='Sub hype! {username} just subscribed PogChamp',
                default='Sub hype! {username} just subscribed PogChamp',
                constraints={
                    'min_str_len': 10,
                    'max_str_len': 400,
                    }),
            ModuleSetting(
                key='resub',
                label='Resub chat message | Available arguments: {username}, {num_months}',
                type='text',
                required=True,
                placeholder='Resub hype! {username} just subscribed, {num_months} months in a row PogChamp <3',
                default='Resub hype! {username} just subscribed, {num_months} months in a row PogChamp <3',
                constraints={
                    'min_str_len': 10,
                    'max_str_len': 400,
                    }),
            ModuleSetting(
                key='whisper_message',
                label='Enable a whisper message for someone who subscribed',
                type='boolean',
                required=True,
                default=False),
            ModuleSetting(
                key='whisper_after',
                label='Whisper the message after X seconds',
                type='number',
                required=True,
                placeholder='',
                default=5,
                constraints={
                    'min_value': 1,
                    'max_value': 120,
                    }),
            ModuleSetting(
                key='new_sub_whisper',
                label='Whisper message for new subs | Available arguments: {username}',
                type='text',
                required=True,
                placeholder='Thank you for subscribing {username} <3',
                default='Thank you for subscribing {username} <3',
                constraints={
                    'min_str_len': 10,
                    'max_str_len': 400,
                    }),
            ModuleSetting(
                key='resub_whisper',
                label='Whisper message for resubs | Available arguments: {username}, {num_months}',
                type='text',
                required=True,
                placeholder='Thank you for subscribing for {num_months} months in a row {username} <3',
                default='Thank you for subscribing for {num_months} months in a row {username} <3',
                constraints={
                    'min_str_len': 10,
                    'max_str_len': 400,
                    }),
                ]

    def __init__(self):
        super().__init__()
        self.new_sub_regex = re.compile('^(\w+) just subscribed!')
        self.valid_usernames = ('twitchnotify', 'pajlada')

    def on_new_sub(self, user):
        """
        A new user just subscribed.
        Send the event to the websocket manager, and send a customized message in chat.
        Also increase the number of active subscribers in the database by one.
        """

        self.bot.kvi['active_subs'].inc()

        payload = {'username': user.username_raw}
        self.bot.websocket_manager.emit('new_sub', payload)

        if self.settings['chat_message'] is True:
            self.bot.say(self.get_phrase('new_sub', **payload))

        if self.settings['whisper_message'] is True:
            self.bot.execute_delayed(self.settings['whisper_after'], self.bot.whisper, (user.username, self.get_phrase('new_sub_whisper', **payload)), )

    def on_resub(self, user, num_months):
        """
        A user just re-subscribed.
        Send the event to the websocket manager, and send a customized message in chat.
        """

        payload = {'username': user.username_raw, 'num_months': num_months}
        self.bot.websocket_manager.emit('resub', payload)

        if self.settings['chat_message'] is True:
            self.bot.say(self.get_phrase('resub', **payload))

        if self.settings['whisper_message'] is True:
            self.bot.execute_delayed(self.settings['whisper_after'], self.bot.whisper, (user.username, self.get_phrase('resub_whisper', **payload)), )

    def on_message(self, source, message, emotes, whisper, urls, event):
        if whisper is False and source.username in self.valid_usernames:
            # Did twitchnotify tell us about a new sub?
            m = self.new_sub_regex.search(message)
            if m:
                username = m.group(1)
                with UserManager.get().get_user_context(username) as user:
                    self.on_new_sub(user)
                    HandlerManager.trigger('on_user_sub', user)

    def on_usernotice(self, source, message, tags):
        if 'msg-id' not in tags or 'msg-param-months' not in tags:
            return

        if tags['msg-id'] == 'resub':
            num_months = int(tags['msg-param-months'])
            self.on_resub(source, num_months)
            HandlerManager.trigger('on_user_resub', source, num_months)

    def enable(self, bot):
        HandlerManager.add_handler('on_message', self.on_message)
        HandlerManager.add_handler('on_usernotice', self.on_usernotice)
        self.bot = bot

    def disable(self, bot):
        HandlerManager.remove_handler('on_message', self.on_message)
        HandlerManager.remove_handler('on_usernotice', self.on_usernotice)

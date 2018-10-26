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
                key='new_prime_sub',
                label='New prime sub chat message | Available arguments: {username}',
                type='text',
                required=True,
                placeholder='Thank you for smashing that prime button! {username} PogChamp',
                default='Thank you for smashing that prime button! {username} PogChamp',
                constraints={
                    'min_str_len': 10,
                    'max_str_len': 400,
                    }),
            ModuleSetting(
                key='new_gift_sub',
                label='New gift sub chat message | Available arguments: {username}, {gifted_by}',
                type='text',
                required=True,
                placeholder='{gifted_by} gifted a fresh sub to {username}! PogChamp',
                default='{gifted_by} gifted a fresh sub to {username}! PogChamp',
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
                key='resub_prime',
                label='Resub chat message (Prime sub) | Available arguments: {username}, {num_months}',
                type='text',
                required=True,
                placeholder='Thank you for smashing it {num_months} in a row {username}',
                default='Thank you for smashing it {num_months} in a row {username}',
                constraints={
                    'min_str_len': 10,
                    'max_str_len': 400,
                    }),
            ModuleSetting(
                key='resub_gift',
                label='Resub chat message (Gift sub) | Available arguments: {username}, {num_months}, {gifted_by}',
                type='text',
                required=True,
                placeholder='{username} got gifted a resub by {gifted_by}, that\'s {num_months} months in a row PogChamp',
                default='{username} got gifted a resub by {gifted_by}, that\'s {num_months} months in a row PogChamp',
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
            ModuleSetting(
                key='grant_points_on_sub',
                label='Give points to user when they subscribe/resubscribe. 0 = off',
                type='number',
                required=True,
                placeholder='',
                default=0,
                constraints={
                    'min_value': 0,
                    'max_value': 50000,
                    }),
                ]

    def __init__(self):
        super().__init__()
        self.new_sub_regex = re.compile('^(\w+) just subscribed')
        self.valid_usernames = ('twitchnotify', 'pajlada')

    def on_sub_shared(self, user):
        if self.settings['grant_points_on_sub'] <= 0:
            return

        user.points += self.settings['grant_points_on_sub']
        self.bot.say('{} was given {} points for subscribing! FeelsAmazingMan'.format(user.username_raw, self.settings['grant_points_on_sub']))

    def on_new_sub(self, user, sub_type, gifted_by=None):
        """
        A new user just subscribed.
        Send the event to the websocket manager, and send a customized message in chat.
        Also increase the number of active subscribers in the database by one.
        """

        self.on_sub_shared(user)

        self.bot.kvi['active_subs'].inc()

        payload = {'username': user.username_raw, 'gifted_by': gifted_by}
        self.bot.websocket_manager.emit('new_sub', payload)

        if self.settings['chat_message'] is True:
            if sub_type == 'Prime':
                self.bot.say(self.get_phrase('new_prime_sub', **payload))
            else:
                if gifted_by:
                    self.bot.say(self.get_phrase('new_gift_sub', **payload))
                else:
                    self.bot.say(self.get_phrase('new_sub', **payload))

        if self.settings['whisper_message'] is True:
            self.bot.execute_delayed(self.settings['whisper_after'], self.bot.whisper, (user.username, self.get_phrase('new_sub_whisper', **payload)), )

    def on_resub(self, user, num_months, sub_type, gifted_by=None):
        """
        A user just re-subscribed.
        Send the event to the websocket manager, and send a customized message in chat.
        """

        self.on_sub_shared(user)

        payload = {'username': user.username_raw, 'num_months': num_months, 'gifted_by': gifted_by}
        self.bot.websocket_manager.emit('resub', payload)

        if self.settings['chat_message'] is True:
            if sub_type == 'Prime':
                self.bot.say(self.get_phrase('resub_prime', **payload))
            else:
                if gifted_by:
                    self.bot.say(self.get_phrase('resub_gift', **payload))
                else:
                    self.bot.say(self.get_phrase('resub', **payload))

        if self.settings['whisper_message'] is True:
            self.bot.execute_delayed(self.settings['whisper_after'], self.bot.whisper, (user.username, self.get_phrase('resub_whisper', **payload)), )

    def on_message(self, source, message, emotes, whisper, urls, event):
        if whisper is False and source.username in self.valid_usernames:
            # Did twitchnotify tell us about a new sub?
            m = self.new_sub_regex.search(message)
            if m and 'subscribed to ' not in message:
                username = m.group(1)
                with UserManager.get().get_user_context(username) as user:
                    self.on_new_sub(user)
                    HandlerManager.trigger('on_user_sub', user)

    def on_usernotice(self, source, message, tags):
        if 'msg-id' not in tags:
            return

        if tags['msg-id'] == 'resub':
            if 'msg-param-months' not in tags:
                log.debug('subalert msg-id is resub, but missing msg-param-months: {}'.format(tags))
                return
            if 'msg-param-sub-plan' not in tags:
                log.debug('subalert msg-id is resub, but missing msg-param-sub-plan: {}'.format(tags))
                return

            # log.debug('msg-id resub tags: {}'.format(tags))

            # TODO: Should we check room id with streamer ID here? Maybe that's for pajbot2 instead
            num_months = int(tags['msg-param-months'])
            self.on_resub(source, num_months, tags['msg-param-sub-plan'])
            HandlerManager.trigger('on_user_resub', source, num_months)
        elif tags['msg-id'] == 'subgift':
            if 'msg-param-months' not in tags:
                log.debug('subalert msg-id is subgift, but missing msg-param-months: {}'.format(tags))
                return
            if 'display-name' not in tags:
                log.debug('subalert msg-id is subgift, but missing display-name: {}'.format(tags))
                return

            num_months = int(tags['msg-param-months'])

            with self.bot.users.get_user_context(tags['msg-param-recipient-user-name']) as receiver:
                if num_months > 1:
                    # Resub
                    self.on_resub(receiver, num_months, tags['msg-param-sub-plan'], tags['display-name'])
                    HandlerManager.trigger('on_user_resub', receiver, num_months)
                else:
                    # New sub
                    self.on_new_sub(receiver, tags['msg-param-sub-plan'], tags['display-name'])
                    HandlerManager.trigger('on_user_sub', receiver)
        elif tags['msg-id'] == 'sub':
            if 'msg-param-sub-plan' not in tags:
                log.debug('subalert msg-id is sub, but missing msg-param-sub-plan: {}'.format(tags))
                return

            self.on_new_sub(source, tags['msg-param-sub-plan'])
            HandlerManager.trigger('on_user_sub', source)
        else:
            log.debug('Unhandled msg-id: {} - tags: {}'.format(tags['msg-id'], tags))

    def enable(self, bot):
        HandlerManager.add_handler('on_message', self.on_message)
        HandlerManager.add_handler('on_usernotice', self.on_usernotice)
        self.bot = bot

    def disable(self, bot):
        HandlerManager.remove_handler('on_message', self.on_message)
        HandlerManager.remove_handler('on_usernotice', self.on_usernotice)

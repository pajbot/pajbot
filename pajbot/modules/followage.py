import datetime
import logging

import pajbot.models
from pajbot.actions import ActionQueue
from pajbot.modules import BaseModule
from pajbot.modules import ModuleSetting
from pajbot.utils import time_since

log = logging.getLogger('pajbot')


class FollowAgeModule(BaseModule):

    ID = __name__.split('.')[-1]
    NAME = 'Follow age'
    DESCRIPTION = 'Makes two commands available: !followage and !followsince'
    CATEGORY = 'Feature'
    SETTINGS = [
            ModuleSetting(
                key='action_followage',
                label='MessageAction for !followage',
                type='options',
                required=True,
                default='say',
                options=[
                    'say',
                    'whisper',
                    ]),
            ModuleSetting(
                key='action_followsince',
                label='MessageAction for !followsince',
                type='options',
                required=True,
                default='say',
                options=[
                    'say',
                    'whisper',
                    ]),
            ]

    def __init__(self):
        super().__init__()
        self.action_queue = ActionQueue()
        self.action_queue.start()

    def load_commands(self, **options):
        # TODO: Have delay modifiable in settings

        self.commands['followage'] = pajbot.models.command.Command.raw_command(self.follow_age,
                delay_all=4,
                delay_user=8,
                description='Check your or someone elses follow age for a channel',
                can_execute_with_whisper=True,
                examples=[
                    pajbot.models.command.CommandExample(None, 'Check your own follow age',
                        chat='user:!followage\n'
                        'bot:pajlada, you have been following Karl_Kons for 4 months and 24 days',
                        description='Check how long you have been following the current streamer (Karl_Kons in this case)').parse(),
                    pajbot.models.command.CommandExample(None, 'Check someone elses follow age',
                        chat='user:!followage NightNacht\n'
                        'bot:pajlada, NightNacht has been following Karl_Kons for 5 months and 4 days',
                        description='Check how long any user has been following the current streamer (Karl_Kons in this case)').parse(),
                    pajbot.models.command.CommandExample(None, 'Check someones follow age for a certain streamer',
                        chat='user:!followage NightNacht forsenlol\n'
                        'bot:pajlada, NightNacht has been following forsenlol for 1 year and 4 months',
                        description='Check how long NightNacht has been following forsenlol').parse(),
                    pajbot.models.command.CommandExample(None, 'Check your own follow age for a certain streamer',
                        chat='user:!followage pajlada forsenlol\n'
                        'bot:pajlada, you have been following forsenlol for 1 year and 3 months',
                        description='Check how long you have been following forsenlol').parse(),
                    ],
                )

        self.commands['followsince'] = pajbot.models.command.Command.raw_command(self.follow_since,
                delay_all=4,
                delay_user=8,
                description='Check from when you or someone else first followed a channel',
                can_execute_with_whisper=True,
                examples=[
                    pajbot.models.command.CommandExample(None, 'Check your own follow since',
                        chat='user:!followsince\n'
                        'bot:pajlada, you have been following Karl_Kons since 04 March 2015, 07:02:01 UTC',
                        description='Check when you first followed the current streamer (Karl_Kons in this case)').parse(),
                    pajbot.models.command.CommandExample(None, 'Check someone elses follow since',
                        chat='user:!followsince NightNacht\n'
                        'bot:pajlada, NightNacht has been following Karl_Kons since 03 July 2014, 04:12:42 UTC',
                        description='Check when NightNacht first followed the current streamer (Karl_Kons in this case)').parse(),
                    pajbot.models.command.CommandExample(None, 'Check someone elses follow since for another streamer',
                        chat='user:!followsince NightNacht forsenlol\n'
                        'bot:pajlada, NightNacht has been following forsenlol since 13 June 2013, 13:10:51 UTC',
                        description='Check when NightNacht first followed the given streamer (forsenlol)').parse(),
                    pajbot.models.command.CommandExample(None, 'Check your follow since for another streamer',
                        chat='user:!followsince pajlada forsenlol\n'
                        'bot:pajlada, you have been following forsenlol since 16 December 1990, 03:06:51 UTC',
                        description='Check when you first followed the given streamer (forsenlol)').parse(),
                    ],
                )

    def check_follow_age(self, bot, source, username, streamer):
        streamer = bot.streamer if streamer is None else streamer.lower()
        age = bot.twitchapi.get_follow_relationship(username, streamer)
        is_self = source.username == username

        if age:
            # Following
            human_age = time_since(datetime.datetime.now().timestamp() - age.timestamp(), 0)
            suffix = 'been following {} for {}'.format(streamer, human_age)
            if is_self:
                bot.send_message_to_user(source, 'You have ' + suffix, method=self.settings['action_followage'])
            else:
                bot.send_message_to_user(source, username + ' has ' + suffix, method=self.settings['action_followage'])
        else:
            # Not following
            suffix = 'not following {}'.format(streamer)
            if is_self:
                bot.send_message_to_user(source, 'You are ' + suffix, method=self.settings['action_followage'])
            else:
                bot.send_message_to_user(source, username + ' is ' + suffix, method=self.settings['action_followage'])

    def check_follow_since(self, bot, source, username, streamer):
        streamer = bot.streamer if streamer is None else streamer.lower()
        follow_since = bot.twitchapi.get_follow_relationship(username, streamer)
        is_self = source.username == username

        if follow_since:
            # Following
            human_age = follow_since.strftime('%d %B %Y, %X')
            suffix = 'been following {} since {} UTC'.format(streamer, human_age)
            if is_self:
                bot.send_message_to_user(source, 'You have ' + suffix, method=self.settings['action_followsince'])
            else:
                bot.send_message_to_user(source, username + ' has ' + suffix, method=self.settings['action_followsince'])
        else:
            # Not following
            suffix = 'not following {}'.format(streamer)
            if is_self:
                bot.send_message_to_user(source, 'You are ' + suffix, method=self.settings['action_followsince'])
            else:
                bot.send_message_to_user(source, username + ' is ' + suffix, method=self.settings['action_followsince'])

    def follow_age(self, **options):
        source = options['source']
        message = options['message']
        bot = options['bot']

        username, streamer = self.parse_message(bot, source, message)

        self.action_queue.add(self.check_follow_age, args=[bot, source, username, streamer])

    def follow_since(self, **options):
        bot = options['bot']
        source = options['source']
        message = options['message']

        username, streamer = self.parse_message(bot, source, message)

        self.action_queue.add(self.check_follow_since, args=[bot, source, username, streamer])

    def parse_message(self, bot, source, message):
        username = source.username
        streamer = None
        if message is not None and len(message) > 0:
            message_split = message.split(' ')
            if len(message_split[0]) and message_split[0].replace('_', '').isalnum():
                username = message_split[0].lower()
            if len(message_split) > 1 and message_split[1].replace('_', '').isalnum():
                streamer = message_split[1]

        return username, streamer

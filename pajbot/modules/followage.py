import logging
import datetime

from pajbot.modules import BaseModule
from pajbot.models.command import Command, CommandExample
from pajbot.tbutil import time_since
from pajbot.actions import ActionQueue

log = logging.getLogger('pajbot')

class FollowAgeModule(BaseModule):

    ID = __name__.split('.')[-1]
    NAME = 'Follow age'
    DESCRIPTION = 'Makes two commands available: !followage and !followsince'

    def __init__(self):
        super().__init__()
        self.action_queue = ActionQueue()
        self.action_queue.start()

    def load_commands(self, **options):
        # TODO: Have delay modifiable in settings

        self.commands['followage'] = Command.raw_command(self.follow_age,
                delay_all=4,
                delay_user=8,
                description='Check your or someone elses follow age for a channel',
                examples=[
                    CommandExample(None, 'Check your own follow age',
                        chat='user:!followage\n'
                        'bot:pajlada, you have been following Karl_Kons for 4 months and 24 days',
                        description='Check how long you have been following the current streamer (Karl_Kons in this case)').parse(),
                    CommandExample(None, 'Check someone elses follow age',
                        chat='user:!followage NightNacht\n'
                        'bot:pajlada, NightNacht has been following Karl_Kons for 5 months and 4 days',
                        description='Check how long any user has been following the current streamer (Karl_Kons in this case)').parse(),
                    CommandExample(None, 'Check someones follow age for a certain streamer',
                        chat='user:!followage NightNacht forsenlol\n'
                        'bot:pajlada, NightNacht has been following forsenlol for 1 year and 4 months',
                        description='Check how long NightNacht has been following forsenlol').parse(),
                    CommandExample(None, 'Check your own follow age for a certain streamer',
                        chat='user:!followage pajlada forsenlol\n'
                        'bot:pajlada, you have been following forsenlol for 1 year and 3 months',
                        description='Check how long you have been following forsenlol').parse(),
                    ],
                )

        self.commands['followsince'] = Command.raw_command(self.follow_since,
                delay_all=4,
                delay_user=8,
                description='Check from when you or someone else first followed a channel',
                examples=[
                    CommandExample(None, 'Check your own follow since',
                        chat='user:!followsince\n'
                        'bot:pajlada, you have been following Karl_Kons since 04 March 2015, 07:02:01 UTC',
                        description='Check when you first followed the current streamer (Karl_Kons in this case)').parse(),
                    CommandExample(None, 'Check someone elses follow since',
                        chat='user:!followsince NightNacht\n'
                        'bot:pajlada, NightNacht has been following Karl_Kons since 03 July 2014, 04:12:42 UTC',
                        description='Check when NightNacht first followed the current streamer (Karl_Kons in this case)').parse(),
                    CommandExample(None, 'Check someone elses follow since for another streamer',
                        chat='user:!followsince NightNacht forsenlol\n'
                        'bot:pajlada, NightNacht has been following forsenlol since 13 June 2013, 13:10:51 UTC',
                        description='Check when NightNacht first followed the given streamer (forsenlol)').parse(),
                    CommandExample(None, 'Check your follow since for another streamer',
                        chat='user:!followsince pajlada forsenlol\n'
                        'bot:pajlada, you have been following forsenlol since 16 December 1990, 03:06:51 UTC',
                        description='Check when you first followed the given streamer (forsenlol)').parse(),
                    ],
                )

    def check_follow_age(self, bot, source, username, streamer):
        streamer = bot.streamer if streamer is None else streamer.lower()
        age = bot.twitchapi.get_follow_relationship(username, streamer)
        if source.username == username:
            if age is False:
                bot.say('{}, you are not following {}'.format(source.username_raw, streamer))
            else:
                bot.say('{}, you have been following {} for {}'.format(source.username_raw, streamer, time_since(datetime.datetime.now().timestamp() - age.timestamp(), 0)))
        else:
            if age is False:
                bot.say('{}, {} is not following {}'.format(source.username_raw, username, streamer))
            else:
                bot.say('{}, {} has been following {} for {}'.format(source.username_raw, username, streamer, time_since(datetime.datetime.now().timestamp() - age.timestamp(), 0)))

    def check_follow_since(self, bot, source, username, streamer):
        streamer = bot.streamer if streamer is None else streamer.lower()
        follow_since = bot.twitchapi.get_follow_relationship(username, streamer)
        if source.username == username:
            if follow_since is False:
                bot.say('{}, you are not following {}'.format(source.username_raw, streamer))
            else:
                bot.say('{}, you have been following {} since {} UTC'.format(
                    source.username_raw,
                    streamer,
                    follow_since.strftime('%d %B %Y, %X')))
        else:
            if follow_since is False:
                bot.say('{}, {} is not following {}'.format(source.username_raw, username, streamer))
            else:
                bot.say('{}, {} has been following {} since {} UTC'.format(
                    source.username_raw,
                    streamer,
                    follow_since.strftime('%d %B %Y, %X')))

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
            potential_user = bot.users.find(message_split[0])
            if potential_user is not None:
                username = potential_user.username

            if len(message_split) > 1 and message_split[1].replace('_', '').isalnum():
                streamer = message_split[1]

        return username, streamer

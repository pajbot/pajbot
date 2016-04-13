import logging

from pajbot.models.command import Command
from pajbot.models.command import CommandExample
from pajbot.modules import BaseModule
from pajbot.modules.basic import BasicCommandsModule

log = logging.getLogger(__name__)


class BTTVEmotesModule(BaseModule):

    ID = __name__.split('.')[-1]
    NAME = '!bttvemotes'
    ENABLED_DEFAULT = True
    DESCRIPTION = 'Lists all custom BTTV Emotes enabled in the stream'
    CATEGORY = 'Feature'
    PARENT_MODULE = BasicCommandsModule

    def reload_bttv_emotes(self, **options):
        bot = options['bot']
        source = options['source']

        bot.whisper(source.username, 'Reloading bttv emotes...')

        bot.action_queue.add(bot.emotes.bttv_emote_manager.update_emotes)

    def get_bttv_emotes(self, **options):
        bot = options['bot']

        if len(bot.emotes.bttv_emote_manager.channel_emotes) > 0:
            bot.say('Active BTTV Emotes in chat: {}'.format(' '.join(bot.emotes.bttv_emote_manager.channel_emotes)))
        else:
            bot.say('No BTTV Emotes active in this chat')

    def load_commands(self, **options):
        get_cmd = Command.raw_command(self.get_bttv_emotes,
                level=100,
                delay_all=3,
                delay_user=6,
                examples=[
                    CommandExample(None, 'Show all active bttv emotes for this channel.',
                        chat='user: !bttvemotes\n'
                        'bot: Active BTTV Emotes in chat: forsenPls gachiGASM',
                        description='').parse(),
                    ])

        reload_cmd = Command.raw_command(self.reload_bttv_emotes,
                level=500,
                delay_all=10,
                delay_user=20,
                examples=[
                    CommandExample(None, 'Reload all active bttv emotes for this channel.',
                        chat='user: !bttvemotes reload\n'
                        'bot>user: Reloading bttv emotes...',
                        description='').parse(),
                    ])

        # The ' ' is there to make things look good in the
        # web interface.
        self.commands['bttvemotes'] = Command.multiaction_command(
                level=100,
                default=' ',
                fallback=' ',
                command='bttvemotes',
                commands={
                    'reload': reload_cmd,
                    ' ': get_cmd,
                    }
                )

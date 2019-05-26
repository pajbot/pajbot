import logging

import pajbot.models
from pajbot.modules import BaseModule
from pajbot.modules.basic import BasicCommandsModule

log = logging.getLogger(__name__)


class FFZEmotesModule(BaseModule):

    ID = __name__.split('.')[-1]
    NAME = '!ffzemotes'
    ENABLED_DEFAULT = True
    DESCRIPTION = 'Lists all custom FFZ Emotes enabled in the stream'
    CATEGORY = 'Feature'
    PARENT_MODULE = BasicCommandsModule

    def reload_ffz_emotes(self, **options):
        bot = options['bot']
        source = options['source']

        bot.whisper(source.username, 'Reloading ffz emotes...')

        bot.action_queue.add(bot.emotes.ffz_emote_manager.update_emotes)

    def get_ffz_emotes(self, **options):
        bot = options['bot']

        if len(bot.emotes.ffz_emote_manager.channel_emotes) > 0:
            base_msg = 'FFZ Emotes:'
            base_len = len(base_msg)
            messages = []
            tmp_message = base_msg
            for emote in bot.emotes.ffz_emote_manager.channel_emotes:
                if len(tmp_message) + len(emote) < 500:
                    tmp_message += ' ' + emote
                else:
                    messages.append(tmp_message)
                    tmp_message = base_msg + ' ' + emote

            if len(tmp_message) > base_len:
                messages.append(tmp_message)

            for msg in messages:
                bot.say(msg)
        else:
            bot.say('No FFZ Emotes active in this chat')

    def load_commands(self, **options):
        get_cmd = pajbot.models.command.Command.raw_command(self.get_ffz_emotes,
                level=100,
                delay_all=15,
                delay_user=60,
                examples=[
                    pajbot.models.command.CommandExample(None, 'Show all active ffz emotes for this channel.',
                        chat='user: !ffzemotes\n'
                        'bot: Active FFZ Emotes in chat: forsenPls gachiGASM',
                        description='').parse(),
                    ])

        reload_cmd = pajbot.models.command.Command.raw_command(self.reload_ffz_emotes,
                level=500,
                delay_all=10,
                delay_user=20,
                examples=[
                    pajbot.models.command.CommandExample(None, 'Reload all active ffz emotes for this channel.',
                        chat='user: !ffzemotes reload\n'
                        'bot>user: Reloading ffz emotes...',
                        description='').parse(),
                    ])

        # The ' ' is there to make things look good in the
        # web interface.
        self.commands['ffzemotes'] = pajbot.models.command.Command.multiaction_command(
                level=100,
                default=' ',
                fallback=' ',
                command='ffzemotes',
                commands={
                    'reload': reload_cmd,
                    ' ': get_cmd,
                    }
                )

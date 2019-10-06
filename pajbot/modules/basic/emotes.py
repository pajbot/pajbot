import logging

from pajbot.managers.emote import BTTVEmoteManager, FFZEmoteManager, TwitchEmoteManager
from pajbot.models.command import Command
from pajbot.models.command import CommandExample
from pajbot.modules import BaseModule
from pajbot.modules.basic import BasicCommandsModule
from pajbot.streamhelper import StreamHelper
from pajbot.utils import split_into_chunks_with_prefix

log = logging.getLogger(__name__)


class EmotesModule(BaseModule):
    ID = __name__.split(".")[-1]
    NAME = "!emotes"
    ENABLED_DEFAULT = True
    DESCRIPTION = "Refresh and list FFZ and BTTV emotes"
    CATEGORY = "Feature"
    PARENT_MODULE = BasicCommandsModule

    def print_emotes(self, manager):
        emotes = manager.channel_emotes
        messages = split_into_chunks_with_prefix(
            [{"prefix": f"{manager.friendly_name} emotes:", "parts": [e.code for e in emotes]}],
            default=f"No {manager.friendly_name} Emotes active in this chat :(",
        )

        for message in messages:
            self.bot.say(message)

    def print_twitch_emotes(self, **rest):
        manager = self.bot.emote_manager.twitch_emote_manager
        messages = split_into_chunks_with_prefix(
            [
                {"prefix": "Subscriber emotes:", "parts": [e.code for e in manager.tier_one_emotes]},
                {"prefix": "T2:", "parts": [e.code for e in manager.tier_two_emotes]},
                {"prefix": "T3:", "parts": [e.code for e in manager.tier_three_emotes]},
            ],
            default=f"Looks like {StreamHelper.get_streamer()} has no subscriber emotes! :(",
        )

        for message in messages:
            self.bot.say(message)

    def reload_cmd(self, manager):
        # manager is an instance of the manager in the bot and the class of the manager on the web interface
        reload_msg = f"Reloading {manager.friendly_name} emotes..."

        def do_reload(bot, source, **rest):
            bot.whisper(source, reload_msg)
            self.bot.action_queue.submit(manager.update_all)

        return Command.raw_command(
            do_reload,
            level=500,
            delay_all=10,
            delay_user=20,
            examples=[
                CommandExample(
                    None,
                    f"Reload all active {manager.friendly_name} emotes for this channel.",
                    chat=f"user: !{manager.friendly_name.lower()}emotes reload\n" + f"bot>user: {reload_msg}",
                ).parse()
            ],
        )

    def print_cmd(self, manager, examples):
        def do_print(**rest):
            self.print_emotes(manager)

        return Command.raw_command(
            do_print,
            level=100,
            delay_all=15,
            delay_user=30,
            examples=[
                CommandExample(
                    None,
                    f"Show all active {manager.friendly_name} emotes for this channel.",
                    chat=f"user: !{manager.friendly_name.lower()}emotes\n"
                    + f"bot: {manager.friendly_name} emotes: {examples}",
                ).parse()
            ],
        )

    def print_twitch_cmd(self):
        return Command.raw_command(
            self.print_twitch_emotes,
            level=100,
            delay_all=15,
            delay_user=30,
            examples=[
                CommandExample(
                    None,
                    f"Show all active sub emotes for {StreamHelper.get_streamer()}.",
                    chat="user: !subemotes\n"
                    "bot: Subscriber emotes: forsenE forsenC forsenK forsenW "
                    "Tier 2: forsenSnus Tier 3: forsen2499",
                ).parse()
            ],
        )

    def load_commands(self, **options):
        cmd_reload_bttv_emotes = self.reload_cmd(
            self.bot.emote_manager.bttv_emote_manager if self.bot else BTTVEmoteManager
        )
        cmd_reload_ffz_emotes = self.reload_cmd(
            self.bot.emote_manager.ffz_emote_manager if self.bot else FFZEmoteManager
        )
        cmd_reload_twitch_emotes = self.reload_cmd(
            self.bot.emote_manager.twitch_emote_manager if self.bot else TwitchEmoteManager
        )
        cmd_print_bttv_emotes = self.print_cmd(
            self.bot.emote_manager.bttv_emote_manager if self.bot else BTTVEmoteManager, "forsenPls gachiGASM"
        )
        cmd_print_ffz_emotes = self.print_cmd(
            self.bot.emote_manager.ffz_emote_manager if self.bot else FFZEmoteManager, "FeelsOkayMan Kapp LULW"
        )

        # The ' ' is there to make things look good in the
        # web interface.
        self.commands["bttvemotes"] = Command.multiaction_command(
            level=100,
            default=" ",
            fallback=" ",
            command="bttvemotes",
            commands={"reload": cmd_reload_bttv_emotes, " ": cmd_print_bttv_emotes},
        )

        self.commands["ffzemotes"] = Command.multiaction_command(
            level=100,
            default=" ",
            fallback=" ",
            command="ffzemotes",
            commands={"reload": cmd_reload_ffz_emotes, " ": cmd_print_ffz_emotes},
        )

        self.commands["subemotes"] = Command.multiaction_command(
            level=100,
            default=" ",
            fallback=" ",
            command="subemotes",
            commands={"reload": cmd_reload_twitch_emotes, " ": self.print_twitch_cmd()},
        )

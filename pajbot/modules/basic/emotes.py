import logging

from pajbot.managers.emote import BTTVEmoteManager, FFZEmoteManager, TwitchEmoteManager, SevenTVEmoteManager
from pajbot.models.command import Command
from pajbot.models.command import CommandExample
from pajbot.modules import BaseModule
from pajbot.modules import ModuleSetting
from pajbot.modules.basic import BasicCommandsModule
from pajbot.streamhelper import StreamHelper
from pajbot.utils import split_into_chunks_with_prefix

log = logging.getLogger(__name__)


class EmotesModule(BaseModule):
    ID = __name__.split(".")[-1]
    NAME = "Emotes"
    ENABLED_DEFAULT = True
    DESCRIPTION = "Refresh and list FFZ, BTTV, 7TV and Sub emotes"
    CATEGORY = "Feature"
    PARENT_MODULE = BasicCommandsModule
    SETTINGS = [
        ModuleSetting(
            key="global_cd",
            label="Global cooldown of all emote-commands (seconds)",
            type="number",
            required=True,
            placeholder="",
            default=5,
            constraints={"min_value": 0, "max_value": 120},
        ),
        ModuleSetting(
            key="user_cd",
            label="Per-user cooldown of all emote-commands (seconds)",
            type="number",
            required=True,
            placeholder="",
            default=15,
            constraints={"min_value": 0, "max_value": 240},
        ),
        ModuleSetting(
            key="level",
            label="Level required to use the commands",
            type="number",
            required=True,
            placeholder="",
            default=100,
            constraints={"min_value": 100, "max_value": 2000},
        ),
        ModuleSetting(
            key="enable_subemotes", label="Enable !subemotes command", type="boolean", required=True, default=True
        ),
        ModuleSetting(
            key="custom_sub_response",
            label="A custom message to override the default !subemotes output format. Leave empty to use default format (1 or multiple messages showing all emotes). | Available arguments: {source}, {streamer}",
            type="text",
            required=False,
            placeholder="@{source}, Channel sub emotes can be found here: https://twitchemotes.com/channels/11148817",
            default="",
            constraints={"max_str_len": 400},
        ),
        ModuleSetting(
            key="enable_ffzemotes", label="Enable !ffzemotes command", type="boolean", required=True, default=True
        ),
        ModuleSetting(
            key="custom_ffz_response",
            label="A custom message to override the default !ffzemotes output format. Leave empty to use default format (1 or multiple messages showing all emotes). | Available arguments: {source}, {streamer}",
            type="text",
            required=False,
            placeholder="@{source}, Channel FFZ emotes can be found here: https://www.frankerfacez.com/channel/pajlada",
            default="",
            constraints={"max_str_len": 400},
        ),
        ModuleSetting(
            key="enable_bttvemotes", label="Enable !bttvemotes command", type="boolean", required=True, default=True
        ),
        ModuleSetting(
            key="custom_bttv_response",
            label="A custom message to override the default !bttvemotes output format. Leave empty to use default format (1 or multiple messages showing all emotes). | Available arguments: {source}, {streamer}",
            type="text",
            required=False,
            placeholder="@{source}, Channel BTTV emotes can be found here: https://betterttv.com/users/550daf6562e6bd0027aedb5e",
            default="",
            constraints={"max_str_len": 400},
        ),
        ModuleSetting(
            key="enable_7tvemotes", label="Enable !7tvemotes command", type="boolean", required=True, default=True
        ),
        ModuleSetting(
            key="custom_7tv_response",
            label="A custom message to override the default !7tvemotes output format. Leave empty to use default format (1 or multiple messages showing all emotes). | Available arguments: {source}, {streamer}",
            type="text",
            required=False,
            placeholder="@{source}, Channel 7TV emotes can be found here: https://7tv.app/users/60baa9493285d8b0b8d9e40f",
            default="",
            constraints={"max_str_len": 400},
        ),
    ]

    def print_emotes(self, source, manager):
        if self.settings[f"custom_{manager.friendly_name.lower()}_response"] != "":
            custom_message = self.settings[f"custom_{manager.friendly_name.lower()}_response"]
            self.bot.say(custom_message.format(streamer=StreamHelper.get_streamer_display(), source=source))
        else:
            emotes = manager.channel_emotes
            messages = split_into_chunks_with_prefix(
                [{"prefix": f"{manager.friendly_name} emotes:", "parts": [e.code for e in emotes]}],
                default=f"No {manager.friendly_name} Emotes active in this chat :(",
            )
            for message in messages:
                self.bot.say(message)

    def print_twitch_emotes(self, source, **rest):
        if self.settings["custom_sub_response"] != "":
            custom_message = self.settings["custom_sub_response"]
            self.bot.say(custom_message.format(streamer=StreamHelper.get_streamer_display(), source=source))
        else:
            manager = self.bot.emote_manager.twitch_emote_manager
            messages = split_into_chunks_with_prefix(
                [
                    {"prefix": "Subscriber emotes:", "parts": [e.code for e in manager.tier_one_emotes]},
                    {"prefix": "T2:", "parts": [e.code for e in manager.tier_two_emotes]},
                    {"prefix": "T3:", "parts": [e.code for e in manager.tier_three_emotes]},
                ],
                default=f"Looks like {StreamHelper.get_streamer_display()} has no subscriber emotes! :(",
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
        def do_print(source, **rest):
            self.print_emotes(source, manager)

        if self.settings[f"custom_{manager.friendly_name.lower()}_response"] != "":
            bot_response = "bot: " + self.settings[f"custom_{manager.friendly_name.lower()}_response"].format(
                source="pajlada", streamer=StreamHelper.get_streamer_display()
            )
        else:
            bot_response = f"bot: {manager.friendly_name} emotes: {examples}"

        return Command.raw_command(
            do_print,
            level=self.settings["level"],
            delay_all=self.settings["global_cd"],
            delay_user=self.settings["user_cd"],
            examples=[
                CommandExample(
                    None,
                    f"Show all active {manager.friendly_name} emotes for this channel.",
                    chat=f"user: !{manager.friendly_name.lower()}emotes\n" + bot_response,
                ).parse()
            ],
        )

    def print_twitch_cmd(self):
        if self.settings["custom_sub_response"] != "":
            bot_response = "bot: " + self.settings["custom_sub_response"].format(
                source="pajlada", streamer=StreamHelper.get_streamer_display()
            )
        else:
            bot_response = (
                "bot: Subscriber emotes: forsenE forsenC forsenK forsenW Tier 2: forsenSnus Tier 3: forsen2499"
            )

        return Command.raw_command(
            self.print_twitch_emotes,
            level=self.settings["level"],
            delay_all=self.settings["global_cd"],
            delay_user=self.settings["user_cd"],
            examples=[
                CommandExample(
                    None,
                    f"Show all active sub emotes for {StreamHelper.get_streamer_display()}.",
                    chat="user: !subemotes\n" + bot_response,
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
        cmd_reload_7tv_emotes = self.reload_cmd(
            self.bot.emote_manager.seventv_emote_manager if self.bot else SevenTVEmoteManager
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
        cmd_print_7tv_emotes = self.print_cmd(
            self.bot.emote_manager.seventv_emote_manager if self.bot else SevenTVEmoteManager, "BasedGod WineTime"
        )

        # The ' ' is there to make things look good in the
        # web interface.
        if self.settings["enable_bttvemotes"]:
            self.commands["bttvemotes"] = Command.multiaction_command(
                delay_all=self.settings["global_cd"],
                delay_user=self.settings["user_cd"],
                level=self.settings["level"],
                default=" ",
                fallback=" ",
                command="bttvemotes",
                commands={"reload": cmd_reload_bttv_emotes, " ": cmd_print_bttv_emotes},
            )

        if self.settings["enable_ffzemotes"]:
            self.commands["ffzemotes"] = Command.multiaction_command(
                delay_all=self.settings["global_cd"],
                delay_user=self.settings["user_cd"],
                level=self.settings["level"],
                default=" ",
                fallback=" ",
                command="ffzemotes",
                commands={"reload": cmd_reload_ffz_emotes, " ": cmd_print_ffz_emotes},
            )

        if self.settings["enable_7tvemotes"]:
            self.commands["7tvemotes"] = Command.multiaction_command(
                delay_all=self.settings["global_cd"],
                delay_user=self.settings["user_cd"],
                level=self.settings["level"],
                default=" ",
                fallback=" ",
                command="7tvemotes",
                commands={"reload": cmd_reload_7tv_emotes, " ": cmd_print_7tv_emotes},
            )

        if self.settings["enable_subemotes"]:
            self.commands["subemotes"] = Command.multiaction_command(
                delay_all=self.settings["global_cd"],
                delay_user=self.settings["user_cd"],
                level=self.settings["level"],
                default=" ",
                fallback=" ",
                command="subemotes",
                commands={"reload": cmd_reload_twitch_emotes, " ": self.print_twitch_cmd()},
            )

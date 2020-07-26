import logging

from pajbot.models.command import Command
from pajbot.models.command import CommandExample
from pajbot.modules import BaseModule
from pajbot.modules import ModuleSetting
from pajbot.modules.basic import BasicCommandsModule
from pajbot.streamhelper import StreamHelper

log = logging.getLogger("pajbot")


class ClipCommandModule(BaseModule):

    ID = __name__.split(".")[-1]
    NAME = "Clip"
    DESCRIPTION = "Enables the usage of the !clip command"
    CATEGORY = "Feature"
    PARENT_MODULE = BasicCommandsModule
    SETTINGS = [
        # TODO: Add VIP support, add discord support, add thumbnail check, add delay support
        ModuleSetting(
            key="subscribers_only",
            label="Only allow subscribers to use the !clip command.",
            type="boolean",
            required=True,
            default=False,
        ),
        ModuleSetting(
            key="online_response",
            label="Message response while the streamer is online | Available arguments: {source}, {streamer}, {clip}",
            type="text",
            required=True,
            placeholder="",
            default="{source}, New clip PogChamp 👉 {clip}",
            constraints={"min_str_len": 1, "max_str_len": 400},
        ),
        ModuleSetting(
            key="offline_response",
            label="Message response if the streamer is offline. Remove text to disable message | Available arguments: {source}, {streamer}",
            type="text",
            required=False,
            placeholder="",
            default="{source}, Cannot clip while {streamer} is offline! BibleThump",
            constraints={"max_str_len": 400},
        ),
        ModuleSetting(
            key="global_cd",
            label="Global cooldown (seconds)",
            type="number",
            required=True,
            placeholder="",
            default=30,
            constraints={"min_value": 0, "max_value": 120},
        ),
        ModuleSetting(
            key="user_cd",
            label="Per-user cooldown (seconds)",
            type="number",
            required=True,
            placeholder="",
            default=60,
            constraints={"min_value": 0, "max_value": 240},
        ),
        ModuleSetting(
            key="level",
            label="Level required to use the command",
            type="number",
            required=True,
            placeholder="",
            default=100,
            constraints={"min_value": 100, "max_value": 2000},
        ),
    ]

    def load_commands(self, **options):
        self.commands["clip"] = Command.raw_command(
            self.clip,
            sub_only=self.settings["subscribers_only"],
            delay_all=self.settings["global_cd"],
            delay_user=self.settings["user_cd"],
            level=self.settings["level"],
            command="clip",
            examples=[
                CommandExample(
                    None,
                    "Make a new clip while the stream is online",
                    chat="user:!clip\n"
                    "bot: "
                    + self.settings["online_response"].format(
                        source="pajlada",
                        streamer=StreamHelper.get_streamer(),
                        clip="https://clips.twitch.tv/ExpensiveWonderfulClamArsonNoSexy",
                    ),
                    description="",
                ).parse()
            ],
        )

    def clip(self, source, message):
        if self.settings["subscribers_only"] and source.subscriber is False:
            return True

        if not self.bot.is_online:
            if self.settings["offline_response"] != "":
                self.bot.say(
                    self.settings["offline_response"].format(source=source, streamer=self.bot.streamer_display)
                )
            return True

        clip_id = self.bot.twitch_helix_api.clip_id()
        clip_url = self.bot.twitch_helix_api.get_clips(clip_id)
        self.bot.say(
            self.settings["online_response"].format(source=source, streamer=self.bot.streamer_display, clip=clip_url)
        )

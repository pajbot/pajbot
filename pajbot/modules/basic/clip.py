import logging

from requests import HTTPError

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
        # TODO: Add discord support
        ModuleSetting(
            key="subscribers_only",
            label="Only allow subscribers to use the !clip command.",
            type="boolean",
            required=True,
            default=False,
        ),
        ModuleSetting(
            key="delay_clip",
            label="Add a delay before the clip is captured (to account for the brief delay between the broadcaster's stream and the viewer's experience).",
            type="boolean",
            required=True,
            default=True,
        ),
        ModuleSetting(
            key="thumbnail_check",
            label="Delay the bot response by 5 seconds to ensure the clip thumbnail has been generated for webchat users.",
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

    def clip(self, bot, source, **rest):
        if self.settings["subscribers_only"] and source.subscriber is False:
            return True

        if not self.bot.is_online:
            if self.settings["offline_response"] != "":
                self.bot.say(
                    self.settings["offline_response"].format(source=source, streamer=self.bot.streamer_display)
                )
            return True

        try:
            if self.settings["delay_clip"] or (source.name == StreamHelper.get_streamer()) is True:
                clip_id = self.bot.twitch_helix_api.create_clip(
                    StreamHelper.get_streamer_id(), self.bot.bot_token_manager, has_delay=True
                )
            else:
                clip_id = self.bot.twitch_helix_api.create_clip(
                    StreamHelper.get_streamer_id(), self.bot.bot_token_manager
                )
        except HTTPError as e:
            if e.response.status_code == 503:
                self.bot.say(f"{source}, Failed to create clip! Does the streamer have clips disabled?")
            elif e.response.status_code != 401:
                self.bot.say(f"{source}, Failed to create clip! Please try again.")
            else:
                self.bot.say(
                    "Error: The bot token does not grant permission to create clips. The bot needs to be re-authenticated to fix this problem."
                )
            return True

        clip_url = "https://clips.twitch.tv/" + clip_id
        if self.settings["thumbnail_check"] is True:
            self.bot.execute_delayed(
                5,
                self.bot.say,
                self.settings["online_response"].format(
                    source=source, streamer=self.bot.streamer_display, clip=clip_url
                ),
            )
        else:
            self.bot.say(
                self.settings["online_response"].format(
                    source=source, streamer=self.bot.streamer_display, clip=clip_url
                )
            )

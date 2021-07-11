import logging

from pajbot.models.command import Command
from pajbot.models.command import CommandExample
from pajbot.modules import BaseModule
from pajbot.modules import ModuleSetting
from pajbot.modules.clr_overlay import CLROverlayModule

log = logging.getLogger(__name__)


class ShowEmoteModule(BaseModule):
    ID = __name__.split(".")[-1]
    NAME = "Show Emote"
    DESCRIPTION = "Show a single emote on screen for a few seconds using !#showemote"
    CATEGORY = "Feature"
    PARENT_MODULE = CLROverlayModule
    SETTINGS = [
        ModuleSetting(
            key="point_cost",
            label="Point cost",
            type="number",
            required=True,
            placeholder="Point cost",
            default=100,
            constraints={"min_value": 0, "max_value": 1000000},
        ),
        ModuleSetting(
            key="token_cost",
            label="Token cost",
            type="number",
            required=True,
            placeholder="Token cost",
            default=0,
            constraints={"min_value": 0, "max_value": 1000000},
        ),
        ModuleSetting(key="sub_only", label="Subscribers only", type="boolean", required=True, default=False),
        ModuleSetting(key="can_whisper", label="Command can be whispered", type="boolean", required=True, default=True),
        ModuleSetting(
            key="global_cd",
            label="Global cooldown (seconds)",
            type="number",
            required=True,
            placeholder="",
            default=5,
            constraints={"min_value": 0, "max_value": 600},
        ),
        ModuleSetting(
            key="user_cd",
            label="Per-user cooldown (seconds)",
            type="number",
            required=True,
            placeholder="",
            default=15,
            constraints={"min_value": 0, "max_value": 1200},
        ),
        ModuleSetting(
            key="command_name",
            label="Command name (i.e. #showemote)",
            type="text",
            required=True,
            placeholder="Command name (no !)",
            default="#showemote",
            constraints={"min_str_len": 1, "max_str_len": 20},
        ),
        ModuleSetting(
            key="emote_whitelist",
            label="Whitelisted emotes (separate by spaces). Leave empty to use the blacklist.",
            type="text",
            required=True,
            placeholder="i.e. Kappa Keepo PogChamp KKona",
            default="",
        ),
        ModuleSetting(
            key="emote_blacklist",
            label="Blacklisted emotes (separate by spaces). Leave empty to allow all emotes.",
            type="text",
            required=True,
            placeholder="i.e. Kappa Keepo PogChamp KKona",
            default="",
        ),
        ModuleSetting(
            key="emote_opacity",
            label="Emote opacity (in percent)",
            type="number",
            required=True,
            placeholder="",
            default=100,
            constraints={"min_value": 0, "max_value": 100},
        ),
        ModuleSetting(
            key="emote_persistence_time",
            label="Time in milliseconds until emotes disappear on screen",
            type="number",
            required=True,
            placeholder="",
            default=5000,
            constraints={"min_value": 500, "max_value": 60000},
        ),
        ModuleSetting(
            key="emote_onscreen_scale",
            label="Scale emotes onscreen by this factor (100 = normal size)",
            type="number",
            required=True,
            placeholder="",
            default=100,
            constraints={"min_value": 0, "max_value": 100000},
        ),
        ModuleSetting(
            key="success_whisper",
            label="Send a whisper when emote was successfully sent",
            type="boolean",
            required=True,
            default=True,
        ),
    ]

    def is_emote_allowed(self, emote_code):
        if len(self.settings["emote_whitelist"].strip()) > 0:
            return emote_code in self.settings["emote_whitelist"]

        return emote_code not in self.settings["emote_blacklist"]

    def show_emote(self, bot, source, args, **rest):
        emote_instances = args["emote_instances"]

        if len(emote_instances) <= 0:
            # No emotes in the given message
            bot.whisper(source, "No valid emotes were found in your message.")
            return False

        first_emote = emote_instances[0].emote

        # request to show emote is ignored but return False ensures user is refunded tokens/points
        if not self.is_emote_allowed(first_emote.code):
            return False

        self.bot.websocket_manager.emit(
            "new_emotes",
            {
                "emotes": [first_emote.jsonify()],
                "opacity": self.settings["emote_opacity"],
                "persistence_time": self.settings["emote_persistence_time"],
                "scale": self.settings["emote_onscreen_scale"],
            },
        )

        if self.settings["success_whisper"]:
            bot.whisper(source, f"Successfully sent the emote {first_emote.code} to the stream!")

    def load_commands(self, **options):
        self.commands[self.settings["command_name"]] = Command.raw_command(
            self.show_emote,
            delay_all=self.settings["global_cd"],
            delay_user=self.settings["user_cd"],
            tokens_cost=self.settings["token_cost"],
            cost=self.settings["point_cost"],
            description="Show an emote on stream!",
            sub_only=self.settings["sub_only"],
            can_execute_with_whisper=self.settings["can_whisper"],
            examples=[
                CommandExample(
                    None,
                    "Show an emote on stream.",
                    chat=f"user:!{self.settings['command_name']} Keepo\n"
                    "bot>user: Successfully sent the emote Keepo to the stream!",
                    description="",
                ).parse()
            ],
        )

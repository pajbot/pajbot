from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, Optional, Set

import logging

from pajbot.models.command import Command, CommandExample
from pajbot.modules import BaseModule, ModuleSetting
from pajbot.modules.clr_overlay import CLROverlayModule

if TYPE_CHECKING:
    from pajbot.bot import Bot
    from pajbot.models.user import User

log = logging.getLogger(__name__)


class ShowEmoteModule(BaseModule):
    ID = __name__.rsplit(".", maxsplit=1)[-1]
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
        ModuleSetting(
            key="emote_whitelist",
            label=CLROverlayModule.ALLOWLIST_LABEL,
            type="text",
            required=True,
            placeholder=CLROverlayModule.EMOTELIST_PLACEHOLDER_TEXT,
            default="",
        ),
        ModuleSetting(
            key="emote_blacklist",
            label=CLROverlayModule.BLOCKLIST_LABEL,
            type="text",
            required=True,
            placeholder=CLROverlayModule.EMOTELIST_PLACEHOLDER_TEXT,
            default="",
        ),
    ]

    def __init__(self, bot: Optional[Bot]) -> None:
        super().__init__(bot)

        self.allowlisted_emotes: Set[str] = set()
        self.blocklisted_emotes: Set[str] = set()

        self.parent_module: Optional[CLROverlayModule] = (
            CLROverlayModule.convert(self.bot.module_manager["clroverlay-group"]) if self.bot else None
        )

    def on_loaded(self) -> None:
        self.allowlisted_emotes = set(
            self.settings["emote_whitelist"].strip().split(" ") if self.settings["emote_whitelist"] else []
        )
        self.blocklisted_emotes = set(
            self.settings["emote_blacklist"].strip().split(" ") if self.settings["emote_blacklist"] else []
        )

    def is_emote_allowed(self, emote_code: str) -> bool:
        if len(self.allowlisted_emotes) > 0:
            return emote_code in self.allowlisted_emotes

        if len(self.blocklisted_emotes) > 0:
            return emote_code not in self.blocklisted_emotes

        if not self.parent_module:
            return True

        return self.parent_module.is_emote_allowed(emote_code)

    def show_emote(self, bot: Bot, source: User, args: Dict[str, Any], **rest: Any) -> bool:
        emote_instances = args["emote_instances"]

        if len(emote_instances) <= 0:
            # No emotes in the given message
            bot.whisper(source, "No valid emotes were found in your message.")
            return False

        first_emote = emote_instances[0].emote

        # request to show emote is ignored but return False ensures user is refunded tokens/points
        if not self.is_emote_allowed(first_emote.code):
            return False

        bot.websocket_manager.emit(
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

        return True

    def load_commands(self, **options: Any) -> None:
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

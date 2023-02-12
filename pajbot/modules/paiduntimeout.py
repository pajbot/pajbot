from __future__ import annotations

from typing import TYPE_CHECKING, Any

import logging

from pajbot.models.command import Command, CommandExample
from pajbot.models.user import User
from pajbot.modules import BaseModule, ModuleSetting

if TYPE_CHECKING:
    from pajbot.bot import Bot

log = logging.getLogger(__name__)


class PaidUntimeoutModule(BaseModule):
    ID = "paiduntimeout"
    NAME = "Paid Untimeout"
    DESCRIPTION = "Allows users to unban themself with points"
    CATEGORY = "Feature"
    SETTINGS = [
        ModuleSetting(
            key="untimeout_enable",
            label="Enable untimeout command! (only remove timeouts, not permanent bans)",
            type="boolean",
            required=True,
            default=True,
        ),
        ModuleSetting(
            key="untimeout_command_name",
            label="Command name (i.e. untimeout)",
            type="text",
            required=True,
            placeholder="Command name (no !)",
            default="untimeout",
            constraints={"min_str_len": 2, "max_str_len": 15},
        ),
        ModuleSetting(
            key="untimeout_cost",
            label="Point cost",
            type="number",
            required=True,
            placeholder="Point cost",
            default=400,
            constraints={"min_value": 0, "max_value": 1000000},
        ),
        ModuleSetting(
            key="unban_enable",
            label="Enable unban command! (removes timeouts and permanent bans)",
            type="boolean",
            required=True,
            default=False,
        ),
        ModuleSetting(
            key="unban_command_name",
            label="Command name (i.e. unban)",
            type="text",
            required=True,
            placeholder="Command name (no !)",
            default="unban",
            constraints={"min_str_len": 2, "max_str_len": 15},
        ),
        ModuleSetting(
            key="unban_cost",
            label="Point cost",
            type="number",
            required=True,
            placeholder="Point cost",
            default=1000,
            constraints={"min_value": 0, "max_value": 1000000},
        ),
    ]

    @staticmethod
    def untimeout_source(bot: Bot, source: User, **rest: Any) -> bool:
        ban_data = bot.twitch_helix_api.get_banned_user(bot.streamer.id, bot.streamer_access_token_manager, source.id)

        if not ban_data:
            bot.whisper(source, "You're not timed out FailFish")
            # Request to be untimed out is ignored, but the return False ensures the user is refunded their points
            return False

        if not ban_data.expires_at:
            bot.whisper(source, "I can't remove your ban with this command FailFish")
            # Request to be untimed out is ignored, but the return False ensures the user is refunded their points
            return False

        bot.untimeout(source)
        bot.whisper(source, "Your timeout has been removed.")
        source.timed_out = False
        return True

    @staticmethod
    def unban_source(bot: Bot, source: User, **rest: Any) -> bool:
        ban_data = bot.twitch_helix_api.get_banned_user(bot.streamer.id, bot.streamer_access_token_manager, source.id)

        if not ban_data:
            bot.whisper(source, "I can't unban you if you aren't banned in the first place FailFish")
            # Request to be unbanned out is ignored, but the return False ensures the user is refunded their points
            return False

        bot.unban(source)
        bot.whisper(source, "You have been unbanned.")
        source.timed_out = False
        source.banned = False
        return True

    def load_commands(self, **options):
        if self.settings["untimeout_enable"]:
            self.commands[
                self.settings["untimeout_command_name"].lower().replace("!", "").replace(" ", "")
            ] = Command.raw_command(
                self.untimeout_source,
                cost=self.settings["untimeout_cost"],
                delay_all=0,
                delay_user=15,
                can_execute_with_whisper=True,
                description="Timed out for no apparent reason? Untimeout yourself using points!",
                examples=[
                    CommandExample(
                        None,
                        f"Untimeout yourself for {self.settings['untimeout_cost']} points",
                        chat=f"user>bot:!{self.settings['untimeout_command_name']}\nbot>user: You have been unbanned.",
                        description="",
                    ).parse()
                ],
            )
        if self.settings["unban_enable"]:
            self.commands[
                self.settings["unban_command_name"].lower().replace("!", "").replace(" ", "")
            ] = Command.raw_command(
                self.unban_source,
                cost=self.settings["unban_cost"],
                delay_all=0,
                delay_user=15,
                can_execute_with_whisper=True,
                description="Banned for no apparent reason? Unban yourself using points!",
                examples=[
                    CommandExample(
                        None,
                        f"Unban yourself for {self.settings['unban_cost']} points",
                        chat=f"user>bot:!{self.settings['unban_command_name']}\nbot>user: You have been unbanned.",
                        description="",
                    ).parse()
                ],
            )

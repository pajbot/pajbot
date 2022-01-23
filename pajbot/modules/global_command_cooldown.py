from __future__ import annotations

from typing import TYPE_CHECKING, Optional

import logging

from pajbot import utils
from pajbot.modules import BaseModule, ModuleSetting

if TYPE_CHECKING:
    from pajbot.bot import Bot

log = logging.getLogger(__name__)


class GlobalCommandCooldown(BaseModule):

    ID = __name__.rsplit(".", maxsplit=1)[-1]
    NAME = "Global command cooldown"
    DESCRIPTION = "Shared cooldown between all commands that opt into this functionality"
    PAGE_DESCRIPTION = "For commands to respect this global command cooldown, you must edit the command in the admin panel and check 'Use global cooldown' or edit the command in the chat and use the flag --use-global-cooldown (e.g. !edit command asciiman --use-global-cooldown or !edit command asciiman --no-use-global-cooldown)"
    CATEGORY = "Moderation"
    SETTINGS = [
        ModuleSetting(
            key="cooldown_duration_online",
            label="Duration of the cooldown in seconds when the stream is online",
            type="number",
            required=True,
            placeholder="",
            default=4,
            constraints={"min_value": 0, "max_value": 3600},
        ),
        ModuleSetting(
            key="cooldown_duration_offline",
            label="Duration of the cooldown in seconds when the stream is offline",
            type="number",
            required=True,
            placeholder="",
            default=4,
            constraints={"min_value": 0, "max_value": 3600},
        ),
    ]

    def __init__(self, bot: Optional[Bot]) -> None:
        super().__init__(bot)

        self.last_run: float = 0

    def run_command(self) -> bool:
        """
        Returns True if the command can be run, return False if it cannot
        """

        if self.bot is None:
            log.warning("Bot not set, global command cooldown module will not work.")
            return True

        cooldown = self.settings["cooldown_duration_offline"]
        if self.bot.is_online:
            cooldown = self.settings["cooldown_duration_online"]

        if cooldown == 0:
            return True

        cur_time = utils.now().timestamp()
        if self.last_run != 0:
            time_since_last_run: float = cur_time - self.last_run
            if time_since_last_run < cooldown:
                return False

        self.last_run = cur_time

        return True

import logging

import requests
from requests import HTTPError

from pajbot.models.command import Command
from pajbot.modules import BaseModule
from pajbot.modules import ModuleSetting

log = logging.getLogger(__name__)


class PNSLModule(BaseModule):

    ID = __name__.split(".")[-1]
    NAME = "Run P&SL lists"
    DESCRIPTION = "Run P&SL lists through the !runpnsl command"
    CATEGORY = "Moderation"
    SETTINGS = [
        ModuleSetting(
            key="level",
            label="Level required to use the command",
            type="number",
            required=True,
            placeholder="",
            default=750,
            constraints={"min_value": 420, "max_value": 2000},
        ),
        ModuleSetting(
            key="per_chunk",
            label="How many lines to process per chunk",
            type="number",
            required=True,
            placeholder="",
            default=30,
            constraints={"min_value": 1, "max_value": 500},
        ),
        ModuleSetting(
            key="chunk_delay",
            label="Delay between chunks (in seconds)",
            type="number",
            required=True,
            placeholder="",
            default=30,
            constraints={"min_value": 5, "max_value": 60},
        ),
        ModuleSetting(
            key="offline_only",
            label="Only allow the PNSL commands to be run while the stream is offline",
            type="boolean",
            required=True,
            default=False,
        ),
    ]

    def __init__(self, bot) -> None:
        super().__init__(bot)

        self.pnsl_token = None

        if bot:
            if "pnsl" in bot.config:
                self.pnsl_token = bot.config["pnsl"].get("token", None)

    def run_pnsl(self, bot, source, message, event, args):
        if self.settings["offline_only"] and self.bot.is_online:
            bot.whisper(source, f"{bot.streamer_display} is live! Skipping PNSL list eval.")
            return False

        base_url = "https://bot.tetyys.com/api/v1/BotLists"

        if not self.pnsl_token:
            bot.whisper(source, f"Missing P&SL token in config.ini. talk to @{bot.admin} BabyRage")
            return False

        guid = message.replace("https://bot.tetyys.com/BotList/", "").replace(
            "https://bot.tetyys.com/api/v1/BotList/", ""
        )

        headers = {"Authorization": f"Bearer {self.pnsl_token}"}

        try:
            res = requests.get(base_url + "/" + guid, headers=headers)
            res.raise_for_status()
        except HTTPError as e:
            log.exception("babyrage")
            if e.response.status_code == 401:
                bot.whisper(source, "Something went wrong with the P&SL request: Access Denied (401)")
            else:
                try:
                    error_data = e.response.json()
                    bot.whisper(
                        source, f"Something went wrong with the P&SL request: {error_data['errors']['Guid'][0]}"
                    )
                except:
                    log.exception("babyrage2")
                    bot.whisper(source, "Something went wrong with the P&SL request")
            return False

        privmsg_list = res.text.split("\n")

        log.info(f"[P&SL] User {source.name} running list {guid} with {len(privmsg_list)} entries")

        bot.privmsg_arr_chunked(
            privmsg_list, per_chunk=self.settings["per_chunk"], chunk_delay=self.settings["chunk_delay"]
        )

    def load_commands(self, **options):
        self.commands["runpnsl"] = Command.raw_command(
            self.run_pnsl,
            delay_all=20,
            delay_user=20,
            level=self.settings["level"],
            description="Run a P&SL list",
            command="runpnsl",
        )
        self.commands["pnslrun"] = self.commands["runpnsl"]

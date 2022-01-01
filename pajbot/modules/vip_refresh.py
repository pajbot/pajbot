import logging

from sqlalchemy import text

from pajbot.managers.db import DBManager
from pajbot.managers.handler import HandlerManager
from pajbot.managers.schedule import ScheduleManager
from pajbot.models.command import Command, CommandExample
from pajbot.modules import BaseModule, ModuleType
from pajbot.utils import time_method

log = logging.getLogger(__name__)


class VIPRefreshModule(BaseModule):
    ID = __name__.split(".")[-1]
    NAME = "VIP refresh"
    DESCRIPTION = "Regularly updates data about who is VIP"
    ENABLED_DEFAULT = True
    HIDDEN = True
    MODULE_TYPE = ModuleType.TYPE_ALWAYS_ENABLED
    CATEGORY = "Internal"

    UPDATE_INTERVAL = 10  # minutes

    def __init__(self, bot):
        super().__init__(bot)
        self.scheduled_job = None

    def update_vip_cmd(self, bot, source, **rest):
        # TODO if you wanted to improve this: Provide the user with feedback
        #   whether the update succeeded, and if yes, how many users were updated
        bot.whisper(source, "Reloading list of VIPs...")
        self._update_vips()

    def _update_vips(self):
        self.bot.privmsg("/vips")

    @staticmethod
    def _parse_pubnotice_for_vips(msg_id, message):
        if msg_id == "no_vips":
            return []

        if msg_id == "vips_success":
            if message.startswith("The VIPs of this channel are: ") and message.endswith("."):
                message = message[30:-1]  # 30 = length of the above "prefix", -1 removes the dot at the end
                return message.split(", ")
            log.warning(
                f"Received vips_success NOTICE message, but actual message did not begin with expected prefix. Message was: {message}"
            )

        return None

    def _on_pubnotice(self, channel: str, msg_id, message) -> None:
        if self.bot is None:
            log.warn("_on_pubnotice failed in VIPRefreshModule because bot is None")
            return

        if channel != self.bot.streamer.login:
            return

        vip_logins = self._parse_pubnotice_for_vips(msg_id, message)

        if vip_logins is not None:
            self.bot.action_queue.submit(self._process_vip_logins, vip_logins)

    @time_method
    def _process_vip_logins(self, vip_logins):
        # Called on the action queue thread, to resolve the logins to user IDs
        vip_basics = self.bot.twitch_helix_api.bulk_get_user_basics_by_login(vip_logins)

        # filter out invalid/deleted/etc. users
        vip_basics = [e for e in vip_basics if e is not None]

        with DBManager.create_session_scope() as db_session:
            db_session.execute(
                text(
                    """
CREATE TEMPORARY TABLE vips(
    id TEXT PRIMARY KEY NOT NULL,
    login TEXT NOT NULL,
    name TEXT NOT NULL
)
ON COMMIT DROP"""
                )
            )

            if len(vip_basics) > 0:
                db_session.execute(
                    text("INSERT INTO vips(id, login, name) VALUES (:id, :login, :name)"),
                    [basics.jsonify() for basics in vip_basics],
                )

            # hint to understand this query: "excluded" is a PostgreSQL keyword that referers
            # to the data we tried to insert but failed (so excluded.login would be equal to :login
            # if we only had one value for :login)
            db_session.execute(
                text(
                    """
WITH updated_users AS (
    INSERT INTO "user"(id, login, name, vip)
        SELECT id, login, name, TRUE FROM vips
    ON CONFLICT (id) DO UPDATE SET
        login = excluded.login,
        name = excluded.name,
        vip = TRUE
    RETURNING id
)
UPDATE "user"
SET
    vip = FALSE
WHERE
    id NOT IN (SELECT * FROM updated_users) AND
    vip IS TRUE"""
                )
            )

        log.info(f"Successfully updated {len(vip_basics)} VIPs")

    def load_commands(self, **options):
        self.commands["reload"] = Command.multiaction_command(
            command="reload",
            commands={
                "vips": Command.raw_command(
                    self.update_vip_cmd,
                    delay_all=120,
                    delay_user=120,
                    level=1000,
                    examples=[
                        CommandExample(
                            None,
                            "Reload who is a Twitch channel VIP",
                            chat="user:!reload vips\nbot>user: Reloading list of VIPs...",
                        ).parse()
                    ],
                )
            },
        )

    def enable(self, bot):
        # Web interface, nothing to do
        if not bot:
            return

        HandlerManager.add_handler("on_pubnotice", self._on_pubnotice)

        # every 10 minutes, send the /vips command (response is received via _on_pubnotice)
        self.scheduled_job = ScheduleManager.execute_every(
            self.UPDATE_INTERVAL * 60, lambda: self.bot.execute_now(self._update_vips)
        )

    def disable(self, bot):
        # Web interface, nothing to do
        if not bot:
            return

        HandlerManager.remove_handler("on_pubnotice", self._on_pubnotice)

        self.scheduled_job.remove()

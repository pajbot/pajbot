import logging

from sqlalchemy import text

from pajbot.managers.db import DBManager
from pajbot.managers.handler import HandlerManager
from pajbot.managers.schedule import ScheduleManager
from pajbot.models.command import Command, CommandExample
from pajbot.modules import BaseModule, ModuleType
from pajbot.utils import time_method

log = logging.getLogger(__name__)


class ModeratorsRefreshModule(BaseModule):
    ID = __name__.split(".")[-1]
    NAME = "Moderators refresh"
    DESCRIPTION = "Regularly updates data about who is moderator"
    ENABLED_DEFAULT = True
    HIDDEN = True
    MODULE_TYPE = ModuleType.TYPE_ALWAYS_ENABLED
    CATEGORY = "Internal"

    UPDATE_INTERVAL = 10  # minutes

    def __init__(self, bot):
        super().__init__(bot)
        self.scheduled_job = None

    def update_moderators_cmd(self, bot, source, **rest):
        # TODO if you wanted to improve this: Provide the user with feedback
        #   whether the update succeeded, and if yes, how many users were updated
        bot.whisper(source, "Reloading list of moderators...")
        self._update_moderators()

    def _update_moderators(self):
        self.bot.privmsg("/mods")

    @staticmethod
    def _parse_pubnotice_for_mods(msg_id, message):
        if msg_id == "no_mods":
            return []

        if msg_id == "room_mods":
            if message.startswith("The moderators of this channel are: "):
                message = message[36:]  # 36 = length of the above "prefix"
                return message.split(", ")
            else:
                log.warning(
                    f"Received room_mods NOTICE message, but actual message did not begin with expected prefix. Message was: {message}"
                )

        return None

    def _on_pubnotice(self, channel: str, msg_id, message) -> None:
        if self.bot is None:
            log.warn("_on_pubnotice failed in ModeratorsRefreshModule because bot is None")
            return

        if channel != self.bot.streamer.login:
            return

        moderator_logins = self._parse_pubnotice_for_mods(msg_id, message)

        if moderator_logins is not None:
            # The broadcaster also has the privileges of a moderator
            if self.bot.streamer.login not in moderator_logins:
                moderator_logins.append(self.bot.streamer.login)

            self.bot.action_queue.submit(self._process_moderator_logins, moderator_logins)

    @time_method
    def _process_moderator_logins(self, moderator_logins):
        # Called on the action queue thread, to resolve the logins to user IDs
        moderator_basics = self.bot.twitch_helix_api.bulk_get_user_basics_by_login(moderator_logins)

        # filter out invalid/deleted/etc. users
        moderator_basics = [e for e in moderator_basics if e is not None]

        with DBManager.create_session_scope() as db_session:
            db_session.execute(
                text(
                    """
CREATE TEMPORARY TABLE moderators(
    id TEXT PRIMARY KEY NOT NULL,
    login TEXT NOT NULL,
    name TEXT NOT NULL
)
ON COMMIT DROP"""
                )
            )

            db_session.execute(
                text("INSERT INTO moderators(id, login, name) VALUES (:id, :login, :name)"),
                [basics.jsonify() for basics in moderator_basics],
            )

            # hint to understand this query: "excluded" is a PostgreSQL keyword that referers
            # to the data we tried to insert but failed (so excluded.login would be equal to :login
            # if we only had one value for :login)
            db_session.execute(
                text(
                    """
WITH updated_users AS (
    INSERT INTO "user"(id, login, name, moderator)
        SELECT id, login, name, TRUE FROM moderators
    ON CONFLICT (id) DO UPDATE SET
        login = excluded.login,
        name = excluded.name,
        moderator = TRUE
    RETURNING id
)
UPDATE "user"
SET
    moderator = FALSE
WHERE
    id NOT IN (SELECT * FROM updated_users) AND
    moderator IS TRUE"""
                )
            )

        log.info(f"Successfully updated {len(moderator_basics)} moderators")

    def load_commands(self, **options):
        self.commands["reload"] = Command.multiaction_command(
            command="reload",
            commands={
                "moderators": Command.raw_command(
                    self.update_moderators_cmd,
                    delay_all=120,
                    delay_user=120,
                    level=1000,
                    examples=[
                        CommandExample(
                            None,
                            "Reload who is a Twitch channel moderator",
                            chat="user:!reload moderators\nbot>user: Reloading moderator status...",
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

        # every 10 minutes, send the /mods command (response is received via _on_pubnotice)
        self.scheduled_job = ScheduleManager.execute_every(
            self.UPDATE_INTERVAL * 60, lambda: self.bot.execute_now(self._update_moderators)
        )

    def disable(self, bot):
        # Web interface, nothing to do
        if not bot:
            return

        HandlerManager.remove_handler("on_pubnotice", self._on_pubnotice)

        self.scheduled_job.remove()

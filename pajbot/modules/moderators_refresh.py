import logging

from pajbot.managers.db import DBManager
from pajbot.managers.handler import HandlerManager
from pajbot.managers.schedule import ScheduleManager
from pajbot.models.command import Command, CommandExample
from pajbot.modules import BaseModule, ModuleType
from pajbot.utils import time_method

from sqlalchemy import text

from requests import HTTPError
from pajbot.apiwrappers.authentication.token_manager import NoTokenError

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
        bot.action_queue.submit(self._update_moderators)

    def _update_moderators(self):
        if self.bot is None:
            log.error("_update_moderators failed in ModeratorsRefreshModule because bot is None")
            return

        try:
            moderator_ids = self.bot.twitch_helix_api.fetch_all_moderators(
                self.bot.streamer.id, self.bot.streamer_access_token_manager
            )

            if moderator_ids is not None:
                # As per the Helix docs, te broadcaster will not be in the response.
                moderator_ids.append(self.bot.streamer.id)

                self.bot.action_queue.submit(self._process_moderator_logins, moderator_ids)
        except NoTokenError:
            log.error(
                "Cannot fetch moderators because no streamer token is present. Have the streamer login with the /streamer_login web route to enable moderator fetch."
            )
            self.bot.send_message("Error: The streamer must be re-authed in order to update moderators.")
            return
        except HTTPError as e:
            if e.response.status_code == 401:
                log.error(
                    "Cannot fetch moderators because no streamer token is present. Have the streamer login with the /streamer_login web route to enable moderator fetch."
                )
                self.bot.send_message("Error: The streamer must be re-authed in order to update moderators.")
                return
            else:
                log.error(f"Failed to update moderators: {e} - {e.response.text}")

    @time_method
    def _process_moderator_ids(self, moderator_ids):
        moderator_basics = self.bot.twitch_helix_api.bulk_get_user_basics_by_id(moderator_ids)

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

        # every 10 minutes, send a helix request to get moderators
        self.scheduled_job = ScheduleManager.execute_every(
            self.UPDATE_INTERVAL * 60, lambda: self.bot.execute_now(self._update_moderators)
        )

    def disable(self, bot):
        # Web interface, nothing to do
        if not bot:
            return

        self.scheduled_job.remove()

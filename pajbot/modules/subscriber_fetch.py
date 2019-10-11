import logging

from sqlalchemy import text

from pajbot.apiwrappers.authentication.token_manager import UserAccessTokenManager, NoTokenError
from pajbot.managers.db import DBManager
from pajbot.managers.redis import RedisManager
from pajbot.managers.schedule import ScheduleManager
from pajbot.models.command import Command, CommandExample
from pajbot.modules import BaseModule
from pajbot.utils import time_method

log = logging.getLogger(__name__)


class SubscriberFetchModule(BaseModule):
    ID = __name__.split(".")[-1]
    NAME = "Subscriber fetch"
    DESCRIPTION = "Fetches a list of subscribers and updates the database"
    ENABLED_DEFAULT = True
    CATEGORY = "Internal"
    HIDDEN = True
    SETTINGS = []

    def update_subs_cmd(self, bot, source, **rest):
        # TODO if you wanted to improve this: Provide the user with feedback
        #   whether the update succeeded, and if yes, how many users were updated
        bot.whisper(source, "Reloading list of subscribers...")
        bot.action_queue.submit(self._update_subscribers)

    @time_method
    def _update_subscribers(self):
        access_token_manager = UserAccessTokenManager(
            api=self.bot.twitch_id_api,
            redis=RedisManager.get(),
            username=self.bot.streamer,
            user_id=self.bot.streamer_user_id,
        )

        try:
            subscriber_ids = self.bot.twitch_helix_api.fetch_all_subscribers(
                self.bot.streamer_user_id, access_token_manager
            )
        except NoTokenError:
            log.warning(
                "Cannot fetch subscribers because no streamer token is present. "
                "Have the streamer log in with the /streamer_login web route to enable subscriber fetch."
            )
            return

        user_basics = self.bot.twitch_helix_api.bulk_get_user_basics_by_id(subscriber_ids)
        # filter out deleted/invalid users
        user_basics = [e for e in user_basics if e is not None]

        # remove broadcaster from sub count
        self.bot.kvi["active_subs"].set(len(user_basics) - 1)

        with DBManager.create_session_scope() as db_session:
            db_session.execute(
                text(
                    """
CREATE TEMPORARY TABLE subscribers(
    id TEXT PRIMARY KEY NOT NULL,
    login TEXT NOT NULL,
    name TEXT NOT NULL
)
ON COMMIT DROP"""
                )
            )

            db_session.execute(
                text("INSERT INTO subscribers(id, login, name) VALUES (:id, :login, :name)"),
                [basics.jsonify() for basics in user_basics],
            )

            # hint to understand this query: "excluded" is a PostgreSQL keyword that referers
            # to the data we tried to insert but failed (so excluded.login would be equal to :login
            # if we only had one value for :login)
            db_session.execute(
                text(
                    """
WITH updated_users AS (
    INSERT INTO "user"(id, login, name, subscriber)
        SELECT id, login, name, TRUE FROM subscribers
    ON CONFLICT (id) DO UPDATE SET
        login = excluded.login,
        name = excluded.name,
        subscriber = TRUE
    RETURNING id
)
UPDATE "user"
SET
    subscriber = FALSE
WHERE
    id NOT IN (SELECT * FROM updated_users) AND
    subscriber IS TRUE"""
                )
            )

        log.info(f"Successfully updated {len(user_basics)} subscribers")

    def load_commands(self, **options):
        self.commands["reload"] = Command.multiaction_command(
            command="reload",
            commands={
                "subscribers": Command.raw_command(
                    self.update_subs_cmd,
                    delay_all=120,
                    delay_user=120,
                    level=1000,
                    examples=[
                        CommandExample(
                            None,
                            f"Reload who is subscriber and who isn't",
                            chat=f"user:!reload subscribers\nbot>user: Reloading list of subscribers...",
                            description="",
                        ).parse()
                    ],
                )
            },
        )

    def enable(self, bot):
        # Web interface, nothing to do
        if not bot:
            return

        # every 10 minutes, add the subscribers update to the action queue
        ScheduleManager.execute_every(10 * 60, lambda: self.bot.action_queue.submit(self._update_subscribers))

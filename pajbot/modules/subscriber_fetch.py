import logging

from pajbot.apiwrappers.authentication.token_manager import UserAccessTokenManager, NoTokenError
from pajbot.managers.redis import RedisManager
from pajbot.managers.schedule import ScheduleManager
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

    def update_subscribers_stage1(self):
        access_token_manager = UserAccessTokenManager(
            api=self.bot.twitch_id_api,
            redis=RedisManager.get(),
            username=self.bot.streamer,
            user_id=self.bot.streamer_user_id,
        )

        try:
            subscribers = self.bot.twitch_helix_api.fetch_all_subscribers(
                self.bot.streamer_user_id, access_token_manager
            )

            self.bot.execute_now(lambda: self.update_subscribers_stage2(subscribers))
        except NoTokenError:
            log.warning(
                "Cannot fetch subscribers because no streamer token is present. "
                "Have the streamer log in with the /streamer_login web route to enable subscriber fetch."
            )
            return

    @time_method
    def update_subscribers_stage2(self, subscribers):
        # remove broadcaster from sub count
        self.bot.kvi["active_subs"].set(len(subscribers) - 1)

        self.bot.users.reset_subs()
        self.bot.users.update_subs(subscribers)

        log.info("Successfully updated %s subscribers", len(subscribers))

    def enable(self, bot):
        # Web interface, nothing to do
        if not bot:
            return

        # every 10 minutes, add the subscribers update to the action queue
        ScheduleManager.execute_every(10 * 60, lambda: self.bot.action_queue.add(self.update_subscribers_stage1))

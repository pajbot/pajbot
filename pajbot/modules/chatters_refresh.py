import logging

from datetime import timedelta
from sqlalchemy import text

from pajbot.managers.db import DBManager
from pajbot.managers.schedule import ScheduleManager
from pajbot.models.command import Command, CommandExample
from pajbot.modules import BaseModule, ModuleSetting
from pajbot.utils import time_method

log = logging.getLogger(__name__)


class ChattersRefreshModule(BaseModule):
    ID = __name__.split(".")[-1]
    NAME = "Chatters refresh"
    DESCRIPTION = "Fetches a list of chatters and updates points/time accordingly - this is required to be turned on in order for the bot to record user time and/or points"
    ENABLED_DEFAULT = True
    CATEGORY = "Internal"
    SETTINGS = [
        ModuleSetting(
            key="base_points_pleb",
            label="Award this points amount every 10 minutes to non-subscribers",
            type="number",
            required=True,
            placeholder="",
            default=2,
            constraints={"min_value": 0, "max_value": 500000},
        ),
        ModuleSetting(
            key="base_points_sub",
            label="Award this points amount every 10 minutes to subscribers",
            type="number",
            required=True,
            placeholder="",
            default=10,
            constraints={"min_value": 0, "max_value": 500000},
        ),
        ModuleSetting(
            key="offline_chat_multiplier",
            label="Apply this multiplier to the awarded points if the stream is currently offline (in percent, 100 = same as online chat, 0 = nothing)",
            type="number",
            required=True,
            placeholder="",
            default=0,
            constraints={"min_value": 0, "max_value": 1000},
        ),
    ]

    UPDATE_INTERVAL = 10  # minutes

    def __init__(self, bot):
        super().__init__(bot)
        self.scheduled_job = None

    def update_chatters_cmd(self, bot, source, **rest):
        # TODO if you wanted to improve this: Provide the user with feedback
        #   whether the update succeeded, and if yes, how many users were updated
        bot.whisper(source, "Reloading list of chatters...")
        bot.action_queue.submit(self._update_chatters, only_last_seen=True)

    @time_method
    def _update_chatters(self, only_last_seen=False):
        chatter_logins = self.bot.twitch_tmi_api.get_chatter_logins_by_login(self.bot.streamer)
        chatter_basics = self.bot.twitch_helix_api.bulk_get_user_basics_by_login(chatter_logins)

        # filter out invalid/deleted/etc. users
        chatter_basics = [e for e in chatter_basics if e is not None]

        is_stream_online = self.bot.stream_manager.online

        if is_stream_online:
            add_time_in_chat_online = timedelta(minutes=self.UPDATE_INTERVAL)
            add_time_in_chat_offline = timedelta(minutes=0)
        else:
            add_time_in_chat_online = timedelta(minutes=0)
            add_time_in_chat_offline = timedelta(minutes=self.UPDATE_INTERVAL)

        add_points_pleb = self.settings["base_points_pleb"]
        add_points_sub = self.settings["base_points_sub"]

        if not is_stream_online:
            offline_chat_multiplier = self.settings["offline_chat_multiplier"] / 100
            add_points_pleb = int(round(add_points_pleb * offline_chat_multiplier))
            add_points_sub = int(round(add_points_sub * offline_chat_multiplier))

        if only_last_seen:
            add_time_in_chat_online = timedelta(minutes=0)
            add_time_in_chat_offline = timedelta(minutes=0)
            add_points_pleb = 0
            add_points_sub = 0

        update_values = [
            {
                **basics.jsonify(),
                "add_points_pleb": add_points_pleb,
                "add_points_sub": add_points_sub,
                "add_time_in_chat_online": add_time_in_chat_online,
                "add_time_in_chat_offline": add_time_in_chat_offline,
            }
            for basics in chatter_basics
        ]

        with DBManager.create_session_scope() as db_session:
            db_session.execute(
                text(
                    """
INSERT INTO "user"(id, login, name, points, time_in_chat_online, time_in_chat_offline, last_seen)
    VALUES (:id, :login, :name, :add_points_pleb, :add_time_in_chat_online, :add_time_in_chat_offline, now())
ON CONFLICT (id) DO UPDATE SET
    points = "user".points + CASE WHEN "user".subscriber THEN :add_points_sub ELSE :add_points_pleb END,
    time_in_chat_online = "user".time_in_chat_online + :add_time_in_chat_online,
    time_in_chat_offline = "user".time_in_chat_offline + :add_time_in_chat_offline,
    last_seen = now()
            """
                ),
                update_values,
            )

        log.info(f"Successfully updated {len(chatter_basics)} chatters")

    def load_commands(self, **options):
        self.commands["reload"] = Command.multiaction_command(
            command="reload",
            commands={
                "chatters": Command.raw_command(
                    self.update_chatters_cmd,
                    delay_all=120,
                    delay_user=120,
                    level=1000,
                    examples=[
                        CommandExample(
                            None,
                            f"Reload who is currently chatting",
                            chat=f"user:!reload chatters\nbot>user: Reloading list of chatters...",
                            description="Note: Updates only last_seen values, does not award points for watching the stream.",
                        ).parse()
                    ],
                )
            },
        )

    def enable(self, bot):
        # Web interface, nothing to do
        if not bot:
            return

        # every 10 minutes, add the chatters update to the action queue
        self.scheduled_job = ScheduleManager.execute_every(
            self.UPDATE_INTERVAL * 60, lambda: self.bot.action_queue.submit(self._update_chatters)
        )

    def disable(self, bot):
        # Web interface, nothing to do
        if not bot:
            return

        self.scheduled_job.remove()

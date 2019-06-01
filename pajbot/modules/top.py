import logging

from pajbot.managers.db import DBManager
from pajbot.managers.redis import RedisManager
from pajbot.models.command import Command
from pajbot.models.user import User
from pajbot.modules import BaseModule
from pajbot.modules import ModuleSetting
from pajbot.streamhelper import StreamHelper
from pajbot.utils import time_since

log = logging.getLogger(__name__)


class TopModule(BaseModule):

    ID = __name__.split(".")[-1]
    NAME = "Top commands"
    DESCRIPTION = "Commands that show the top X users of something"
    CATEGORY = "Feature"
    SETTINGS = [
        ModuleSetting(
            key="num_top",
            label="How many people we should list",
            type="number",
            required=True,
            placeholder="min 1, max 5",
            default=3,
            constraints={"min_value": 1, "max_value": 5},
        ),
        ModuleSetting(
            key="enable_topchatters",
            label="Enable the !topchatters command (most messages)",
            type="boolean",
            required=True,
            default=False,
        ),
        ModuleSetting(
            key="enable_topwatchers",
            label="Enable the !topwatchers command (most time spent watching the stream)",
            type="boolean",
            required=True,
            default=False,
        ),
        ModuleSetting(
            key="enable_topoffline",
            label="Enable the !topoffline command (most time spent in offline chat)",
            type="boolean",
            required=True,
            default=False,
        ),
        ModuleSetting(
            key="enable_toppoints",
            label="Enable the !toppoints command (most points)",
            type="boolean",
            required=True,
            default=False,
        ),
    ]

    def top_chatters(self, **options):
        """ TODO: use username_raw somehow """
        bot = options["bot"]

        data = []
        redis = RedisManager.get()

        for user in redis.zrevrangebyscore(
            "{streamer}:users:num_lines".format(streamer=StreamHelper.get_streamer()),
            "+inf",
            "-inf",
            start=0,
            num=self.settings["num_top"],
            withscores=True,
            score_cast_func=int,
        ):
            data.append("{} ({})".format(user[0], user[1]))

        bot.say("Top {num_top} chatters: {data}".format(num_top=self.settings["num_top"], data=", ".join(data)))

    def top_watchers(self, **options):
        bot = options["bot"]

        data = []
        with DBManager.create_session_scope() as db_session:
            for user in db_session.query(User).order_by(User.minutes_in_chat_online.desc())[: self.settings["num_top"]]:
                data.append(
                    "{user.username_raw} ({time_spent})".format(
                        user=user, time_spent=time_since(user.minutes_in_chat_online * 60, 0, time_format="short")
                    )
                )

        bot.say("Top {num_top} watchers: {data}".format(num_top=self.settings["num_top"], data=", ".join(data)))

    def top_offline(self, **options):
        bot = options["bot"]

        data = []
        with DBManager.create_session_scope() as db_session:
            for user in db_session.query(User).order_by(User.minutes_in_chat_offline.desc())[
                : self.settings["num_top"]
            ]:
                data.append(
                    "{user.username_raw} ({time_spent})".format(
                        user=user, time_spent=time_since(user.minutes_in_chat_offline * 60, 0, time_format="short")
                    )
                )

        bot.say("Top {num_top} offliners: {data}".format(num_top=self.settings["num_top"], data=", ".join(data)))

    def top_points(self, **options):
        bot = options["bot"]

        data = []
        with DBManager.create_session_scope() as db_session:
            for user in db_session.query(User).order_by(User.points.desc())[: self.settings["num_top"]]:
                data.append("{user.username_raw} ({user.points})".format(user=user))

        bot.say("Top {num_top} banks: {data}".format(num_top=self.settings["num_top"], data=", ".join(data)))

    def load_commands(self, **options):
        if self.settings["enable_topchatters"]:
            self.commands["topchatters"] = Command.raw_command(self.top_chatters)

        if self.settings["enable_topwatchers"]:
            self.commands["topwatchers"] = Command.raw_command(self.top_watchers)

        if self.settings["enable_topoffline"]:
            self.commands["topoffline"] = Command.raw_command(self.top_offline)

        if self.settings["enable_toppoints"]:
            self.commands["toppoints"] = Command.raw_command(self.top_points)

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
    DESCRIPTION = "Commands that show the top X users of something or top X emotes"
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
            key="num_top_emotes",
            label="How many emotes we should list",
            type="number",
            required=True,
            placeholder="min 1, max 10",
            default=5,
            constraints={"min_value": 1, "max_value": 10},
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
        ModuleSetting(
            key="enable_topemotes",
            label="Enable the !topemotes command (top used emotes)",
            type="boolean",
            required=True,
            default=False,
        ),
    ]

    def top_chatters(self, bot, **rest):
        data = []
        with DBManager.create_session_scope() as db_session:
            for user in db_session.query(User).order_by(User.num_lines.desc()).limit(self.settings["num_top"]):
                data.append(f"{user} ({user.num_lines})")

        bot.say(f"Top {self.settings['num_top']} chatters: {', '.join(data)}")

    def top_watchers(self, bot, **rest):
        data = []
        with DBManager.create_session_scope() as db_session:
            for user in (
                db_session.query(User).order_by(User.time_in_chat_online.desc()).limit(self.settings["num_top"])
            ):
                data.append(f"{user} ({time_since(user.time_in_chat_online.total_seconds(), 0, time_format='short')})")

        bot.say(f"Top {self.settings['num_top']} watchers: {', '.join(data)}")

    def top_offline(self, bot, **rest):
        data = []
        with DBManager.create_session_scope() as db_session:
            for user in (
                db_session.query(User).order_by(User.time_in_chat_offline.desc()).limit(self.settings["num_top"])
            ):
                data.append(f"{user} ({time_since(user.time_in_chat_offline.total_seconds(), 0, time_format='short')})")

        bot.say(f"Top {self.settings['num_top']} offline chatters: {', '.join(data)}")

    def top_points(self, bot, **rest):
        data = []
        with DBManager.create_session_scope() as db_session:
            for user in db_session.query(User).order_by(User.points.desc()).limit(self.settings["num_top"]):
                data.append(f"{user} ({user.points})")

        bot.say(f"Top {self.settings['num_top']} banks: {', '.join(data)}")

    def top_emotes(self, bot, **rest):
        redis = RedisManager.get()
        streamer = StreamHelper.get_streamer()
        num_emotes = self.settings["num_top_emotes"]

        top_emotes = {
            emote: emote_count
            for emote, emote_count in sorted(
                redis.zscan_iter(f"{streamer}:emotes:count"), key=lambda e_ecount_pair: e_ecount_pair[1], reverse=True
            )[:num_emotes]
        }
        if top_emotes:
            top_list_str = ", ".join(f"{emote} ({emote_count:,.0f})" for emote, emote_count in top_emotes.items())
            bot.say(f"Top {num_emotes} emotes: {top_list_str}")
        else:
            bot.say("No emote data available")

    def load_commands(self, **options):
        if self.settings["enable_topchatters"]:
            self.commands["topchatters"] = Command.raw_command(self.top_chatters)

        if self.settings["enable_topwatchers"]:
            self.commands["topwatchers"] = Command.raw_command(self.top_watchers)

        if self.settings["enable_topoffline"]:
            self.commands["topoffline"] = Command.raw_command(self.top_offline)

        if self.settings["enable_toppoints"]:
            self.commands["toppoints"] = Command.raw_command(self.top_points)

        if self.settings["enable_topemotes"]:
            self.commands["topemotes"] = Command.raw_command(self.top_emotes)

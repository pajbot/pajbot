import logging
from datetime import datetime, date, timedelta
import random
import requests
import pytz

from pajbot.models.command import Command
from pajbot.managers.db import DBManager
from pajbot.modules import BaseModule
from pajbot.modules import ModuleSetting
from pajbot.models.user import User
from pajbot.utils import now

from sqlalchemy import and_

log = logging.getLogger(__name__)


class TaxationModule(BaseModule):
    AUTHOR = "TroyDota"
    ID = __name__.split(".")[-1]
    NAME = "Taxation"
    DESCRIPTION = "Forces users to pay tax"
    CATEGORY = "Feature"
    SETTINGS = [
        ModuleSetting(
            key="timeout_duration",
            label="Timeout duration, 0 for disable",
            type="number",
            required=True,
            placeholder="",
            default=86400,
            constraints={"min_value": 0},
        ),
        ModuleSetting(
            key="min_lines",
            label="Minimum number of lines for a user to be considered, 0 for disable",
            type="number",
            required=True,
            placeholder="",
            default=500,
            constraints={"min_value": 0},
        ),
        ModuleSetting(
            key="default_process_time_days",
            label="Default number of days to process",
            type="number",
            required=True,
            placeholder="",
            default=7,
            constraints={"min_value": 1, "max_value": 30},
        ),
        ModuleSetting(
            key="default_timezone",
            label="Default timezone",
            type="options",
            required=True,
            default="UTC",
            options=pytz.all_timezones,
        ),
        ModuleSetting(
            key="minimum_taxes",
            label="Minimum number of taxes to avoid a ban if the user is not a sub, 0 for disable",
            type="number",
            required=True,
            placeholder="",
            default=2,
            constraints={"min_value": 0},
        ),
        ModuleSetting(
            key="minimum_taxes_subs",
            label="Minimum number of taxes to avoid a ban if the user is subbed, 0 for disable",
            type="number",
            required=True,
            placeholder="",
            default=2,
            constraints={"min_value": 0},
        ),
        ModuleSetting(
            key="minimum_days_paid_reward",
            label="Minimum number of days required to recieve a reward",
            type="number",
            required=True,
            placeholder="",
            default=7,
            constraints={"min_value": 1},
        ),
        ModuleSetting(
            key="number_points_tax",
            label="Points to give when they hit the threshold, 0 for disable",
            type="number",
            required=True,
            placeholder="",
            default=15000,
            constraints={"min_value": 0},
        ),
        ModuleSetting(
            key="number_points_top",
            label="Points to the user with the most taxes paid, 0 for disable",
            type="number",
            required=True,
            placeholder="",
            default=15000,
            constraints={"min_value": 0},
        ),
        ModuleSetting(
            key="reward_id",
            label="ID of tax redeem reward",
            type="text",
            required=True,
            default="",
            constraints={"min_str_len": 36, "max_str_len": 36},
        ),
    ]

    def process_tax(self, bot, source, message, **rest):
        self._process_tax(message)

    def calculate_tax(self, bot, source, message, **rest):
        self._process_tax(message, execute=False)

    def _process_tax(self, message, execute=True):
        process_time = self.settings["default_process_time_days"]

        after_date = datetime.combine(date.today(), datetime.min.time()).replace(
            tzinfo=pytz.timezone(self.settings["default_timezone"])
        ) - timedelta(days=process_time)

        with DBManager.create_session_scope() as db_session:
            users_active = (
                db_session.query(User)
                .filter(
                    and_(
                        User.last_active > after_date,
                        User.moderator.isnot(True),
                        User.ignored.isnot(True),
                        User.banned.isnot(True),
                        User.num_lines >= self.settings["min_lines"],
                    )
                )
                .all()
            )  # ignore the mods or users who are ignored/banned by the bot

            users_dict = {}
            for user in users_active:
                users_dict[user.id] = {
                    "user": user,
                    "redemption_costs": 0,
                    "days_redeemed": [False for x in range(process_time)],
                }

            json_data = {
                "request": "channel",
                "category": "rewards",
                "room_id": self.bot.streamer_user_id,
                "reward_id": self.settings["reward_id"],
                "after_date": after_date.isoformat(),
            }

            request = requests.post("https://chatlogs.troybot.live/query", json=json_data)
            if request.status_code != 200:
                self.bot.say("Api is currently down 4Head")
                return False

            resp = request.json()["data"]
            for item in resp:
                user_id = item["user_id"]
                if user_id in users_dict:
                    users_dict[user_id]["redemption_costs"] += int(item["cost"])
                    index = (
                        datetime.fromisoformat(item["redeemed_at"]).astimezone(
                            pytz.timezone(self.settings["default_timezone"])
                        )
                        - after_date
                    ).days - 1
                    users_dict[user_id]["days_redeemed"][index] = True

            users_to_timeout = []
            users_to_award = []
            action_messages = []

            for item in users_dict:
                user_dict_obj = users_dict[item]
                min_tax = self.settings[f"minimum_taxes{'_subs' if user_dict_obj['user'].subscriber else ''}"]
                paid_count = 0
                dates_paid = user_dict_obj["days_redeemed"]
                for value in dates_paid:
                    if value is True:
                        paid_count += 1

                if paid_count < min_tax:
                    users_to_timeout.append(user_dict_obj)

                if paid_count >= self.settings["minimum_days_paid_reward"]:
                    users_to_award.append(user_dict_obj)

            if self.settings["timeout_duration"] and users_to_timeout:
                check_user_timeouts = (
                    self.bot.twitch_helix_api.bulk_fetch_user_bans(
                        "user_id",
                        [user_dict_obj["user"].id for user_dict_obj in users_to_timeout],
                        self.bot.streamer_user_id,
                        self.bot.streamer_access_token_manager,
                    )
                    if users_to_timeout
                    else []
                )

                number_of_timeouts = 0

                for user_dict_obj in random.sample(users_to_timeout, 300):  # Hard limit of 300 timeouts.
                    user = user_dict_obj["user"]
                    timeout = check_user_timeouts[user.id]
                    if timeout is not None:
                        if not timeout["expires_at"]:
                            continue
                        new_timeout = (
                            datetime.strptime(timeout["expires_at"], "%Y-%m-%dT%H:%M:%S%z") - now()
                        ).total_seconds() + self.settings["timeout_duration"]
                    else:
                        new_timeout = self.settings["timeout_duration"]
                    new_timeout = int(60 * 60 * 24 * 14 if new_timeout > 60 * 60 * 24 * 14 else new_timeout)
                    if new_timeout > 0:
                        if execute:
                            self.bot.timeout(user, new_timeout, "Failed to pay taxes")
                        number_of_timeouts += 1
                action_messages.append(f"Timedout {number_of_timeouts} users for not paying tax.")

            if self.settings["number_points_tax"]:
                for item in users_to_award:
                    if execute:
                        item["user"].points += self.settings["number_points_tax"]
                action_messages.append(
                    f"Awarded {len(users_to_award)} users {self.settings['number_points_tax']} points for paying tax."
                )

            if self.settings["number_points_top"]:
                top_list = []
                top_val = -1
                second_list = []
                second_val = -1
                for user_data in users_dict.values():
                    cost = user_data["redemption_costs"]
                    if cost > top_val:
                        second_list = top_list
                        top_list = [user_data["user"]]
                        second_val = top_val
                        top_val = cost
                    elif cost == top_val:
                        top_list.append(user_data["user"])
                    elif cost > second_val:
                        second_list = [user_data["user"]]
                        second_val = cost
                    elif cost == second_val:
                        second_list.append(user_data["user"])
                top_users = []
                for user in top_list:
                    top_users.append(user.name)
                    if execute:
                        user.points += self.settings["number_points_top"]
                second_place_users = [user.name for user in second_list]
                if top_val > 0:
                    action_messages.append(
                        f"Awarded {', '.join(top_users)} {self.settings['number_points_top']} points for paying the most tax at {top_val} channel points "
                        + f"Second place was {', '.join(second_place_users)} for paying {second_val} channel points"
                        if second_val > 0
                        else ""
                    )

            self.bot.me(" ".join(action_messages))

    def load_commands(self, **options):
        self.commands["processtax"] = Command.raw_command(
            self.process_tax,
            level=1000,
            description=f"Processes the tax for the last {self.settings['default_process_time_days']} days",
        )
        self.commands["calculatetax"] = Command.raw_command(
            self.calculate_tax,
            level=1000,
            description=f"Calculates the tax for the last {self.settings['default_process_time_days']} days",
        )

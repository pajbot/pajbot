import logging

from pajbot.managers.db import DBManager
from pajbot.models.command import Command
from pajbot.models.command import CommandExample
from pajbot.models.user import User
from pajbot.modules import BaseModule
from pajbot.modules import ModuleSetting

from sqlalchemy import text

log = logging.getLogger(__name__)


class MassPointsModule(BaseModule):
    ID = __name__.split(".")[-1]
    NAME = "Mass Points"
    DESCRIPTION = "Give points to everyone watching the stream"
    CATEGORY = "Feature"
    SETTINGS = [
        ModuleSetting(
            key="sub_points",
            label="Award this amount of points to subs for every pleb point",
            type="number",
            required=True,
            placeholder="1",
            default=1,
            constraints={"min_value": 0, "max_value": 100},
        )
    ]

    def load_commands(self, **options):
        self.commands["masspoints"] = Command.raw_command(
            self.command_masspoints,
            level=500,
            description="Give a specific number of points to everyone watching the stream",
            examples=[
                CommandExample(
                    None,
                    "Give 300 points (for a fisting)",
                    chat="user:!masspoints 300\n" "bot: pajlada just gave 300 points to 159 viewers! Enjoy FeelsGoodMan",
                    description="Give points to all chatters",
                ).parse()
            ],
        )

    def command_masspoints(self, bot, source, message, **rest):
        if not message:
            return False

        points_argument = message.split()[0]
        givePoints = 0

        try:
            givePoints = int(points_argument)
        except ValueError:
            bot.whisper(source, "Invalid Usage, please specify a whole number.")
            return False

        # If they enter 0, there is no point in doing an update.
        if givePoints == 0:
            return

        current_chatters = bot.twitch_tmi_api.get_chatter_logins_by_login(bot.streamer)
        num_users = len(current_chatters)
        if not current_chatters:
            bot.say("Error fetching chatters")
            return False

        user_basics = bot.twitch_helix_api.bulk_get_user_basics_by_login(current_chatters)

        # filter out invalid/deleted/etc. users
        user_basics = [e for e in user_basics if e is not None]

        with DBManager.create_session_scope() as db_session:
            subscribers = [user.id for user in db_session.query(User).filter_by(subscriber=True).all()]
            num_points = lambda user: givePoints + (
                givePoints * self.settings["sub_points"] if user.id in subscribers else 0
            )
            update_values = [{**basics.jsonify(), "add_points": num_points(basics)} for basics in user_basics]
            db_session.execute(
                text(
                    """
INSERT INTO "user"(id, login, name, points)
    VALUES (:id, :login, :name, :add_points)
ON CONFLICT (id) DO UPDATE SET
    points = "user".points + :add_points
WHERE "user".ignored = False and "user".banned = False and "user".num_lines > 5
            """
                ),
                update_values,
            )
        bot.say(f"{source} just gave {num_users} viewers {givePoints} points each! Enjoy FeelsGoodMan")

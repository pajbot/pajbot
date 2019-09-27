import logging

import sqlalchemy
from sqlalchemy import BOOLEAN, INT
from sqlalchemy import Column
from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy_utc import UtcDateTime

from pajbot import utils
from pajbot.managers.db import Base
from pajbot.managers.db import DBManager
from pajbot.models.command import Command
from pajbot.modules.base import BaseModule
from pajbot.modules.base import ModuleSetting

log = logging.getLogger(__name__)


class PredictionRun(Base):
    __tablename__ = "prediction_run"

    id = Column(INT, primary_key=True)
    type = Column(INT, nullable=False, server_default="0")
    winner_id = Column(INT, nullable=True)
    started = Column(UtcDateTime(), nullable=False)
    ended = Column(UtcDateTime(), nullable=True)
    open = Column(BOOLEAN, nullable=False, default=True, server_default=sqlalchemy.sql.expression.true())

    def __init__(self, type):
        self.id = None
        self.type = type
        self.winner_id = None
        self.started = utils.now()
        self.ended = None


class PredictionRunEntry(Base):
    __tablename__ = "prediction_run_entry"

    id = Column(INT, primary_key=True)
    prediction_run_id = Column(INT, ForeignKey("prediction_run.id"), nullable=False)
    user_id = Column(INT, nullable=False)
    prediction = Column(INT, nullable=False)

    user = relationship(
        "User",
        cascade="",
        uselist=False,
        lazy="noload",
        foreign_keys="User.id",
        primaryjoin="User.id==PredictionRunEntry.user_id",
    )

    def __init__(self, prediction_run_id, user_id, prediction):
        self.id = None
        self.prediction_run_id = prediction_run_id
        self.user_id = user_id
        self.prediction = prediction


class PredictModule(BaseModule):

    ID = __name__.split(".")[-1]
    NAME = "Prediction module"
    DESCRIPTION = "Handles predictions of arena wins"
    CATEGORY = "Feature"
    SETTINGS = [
        ModuleSetting(
            key="challenge_name",
            label="The name of the challenge",
            type="text",
            required=True,
            placeholder="The name of the challenge",
            default="100in10 arena",
        ),
        ModuleSetting(
            key="max_wins",
            label="The maximum amount of wins the user can predict",
            type="number",
            required=True,
            placeholder="The maximum amount of wins the user can bet",
            default=120,
            constraints={"min_value": 0},
        ),
        ModuleSetting(key="sub_only", label="Sub only", type="boolean", required=True, default=True),
        ModuleSetting(
            key="mini_command",
            label="Mini predict command (Leave empty to disable)",
            type="text",
            required=True,
            default="",
        ),
        ModuleSetting(
            key="mini_max_wins",
            label="The maximum amount of wins the user can predict in the mini prediction",
            type="number",
            required=True,
            placeholder="The maximum amount of wins the user can bet",
            default=12,
            constraints={"min_value": 0},
        ),
    ]

    def load_commands(self, **options):
        self.commands["predict"] = Command.multiaction_command(
            level=100,
            default="vote",
            fallback="vote",
            delay_all=0,
            delay_user=0,
            commands={
                "vote": Command.raw_command(
                    self.predict,
                    delay_all=0,
                    delay_user=10,
                    sub_only=self.settings["sub_only"],
                    can_execute_with_whisper=True,
                    description="Predict how many wins will occur in the "
                    + self.settings["challenge_name"]
                    + " challenge",
                ),
                "new": Command.raw_command(
                    self.new_predict,
                    delay_all=10,
                    delay_user=10,
                    description="Starts a new " + self.settings["challenge_name"] + " run",
                    level=750,
                ),
                "end": Command.raw_command(
                    self.end_predict,
                    delay_all=10,
                    delay_user=10,
                    description="Ends a " + self.settings["challenge_name"] + " run",
                    level=750,
                ),
                "close": Command.raw_command(
                    self.close_predict,
                    delay_all=10,
                    delay_user=10,
                    description="Close submissions to the latest " + self.settings["challenge_name"] + " run",
                    level=750,
                ),
            },
        )

        # XXX: DEPRECATED, WILL BE REMOVED
        self.commands["newpredict"] = Command.raw_command(
            self.new_predict_depr,
            delay_all=10,
            delay_user=10,
            description="Starts a new " + self.settings["challenge_name"] + " run",
            level=750,
        )
        self.commands["endpredict"] = Command.raw_command(
            self.end_predict_depr,
            delay_all=10,
            delay_user=10,
            description="Ends a " + self.settings["challenge_name"] + " run",
            level=750,
        )
        self.commands["closepredict"] = Command.raw_command(
            self.close_predict_depr,
            delay_all=10,
            delay_user=10,
            description="Close submissions to the latest " + self.settings["challenge_name"] + " run",
            level=750,
        )

        mini_command = self.settings["mini_command"].lower().replace("!", "").replace(" ", "")
        if len(mini_command) > 0:
            self.commands[mini_command] = Command.multiaction_command(
                level=100,
                default="vote",
                fallback="vote",
                delay_all=0,
                delay_user=0,
                commands={
                    "vote": Command.raw_command(
                        self.mini_predict,
                        delay_all=0,
                        delay_user=10,
                        sub_only=self.settings["sub_only"],
                        can_execute_with_whisper=True,
                        description="Predict how many wins will occur in the "
                        + self.settings["challenge_name"]
                        + " challenge",
                    ),
                    "new": Command.raw_command(
                        self.mini_new_predict,
                        delay_all=10,
                        delay_user=10,
                        description="Starts a new " + self.settings["challenge_name"] + " run",
                        level=750,
                    ),
                    "end": Command.raw_command(
                        self.mini_end_predict,
                        delay_all=10,
                        delay_user=10,
                        description="Ends a " + self.settings["challenge_name"] + " run",
                        level=750,
                    ),
                    "close": Command.raw_command(
                        self.mini_close_predict,
                        delay_all=10,
                        delay_user=10,
                        description="Close submissions to the latest " + self.settings["challenge_name"] + " run",
                        level=750,
                    ),
                },
            )

    def new_predict_depr(self, **options):
        bot = options["bot"]
        source = options["source"]

        bot.whisper(source.username, 'This command is deprecated, please use "!predict new" in the future.')
        self.new_predict(**options)

    def end_predict_depr(self, **options):
        bot = options["bot"]
        source = options["source"]

        bot.whisper(source.username, 'This command is deprecated, please use "!predict end" in the future.')
        self.end_predict(**options)

    def close_predict_depr(self, **options):
        bot = options["bot"]
        source = options["source"]

        bot.whisper(source.username, 'This command is deprecated, please use "!predict close" in the future.')
        self.close_predict(**options)

    def shared_predict(self, bot, source, message, type):
        if type == 0:
            max_wins = self.settings["max_wins"]
        else:
            max_wins = self.settings["mini_max_wins"]
        example_wins = round(max_wins / 2)
        bad_command_message = "{username}, Missing or invalid argument to command. Valid argument could be {example_wins} where {example_wins} is a number between 0 and {max_wins} (inclusive).".format(
            username=source.username_raw, example_wins=example_wins, max_wins=max_wins
        )

        if source.id is None:
            log.warning("Source ID is NONE, attempting to salvage by commiting users to the database.")
            log.info("New ID is: {}".format(source.id))
            bot.whisper(source.username, "uuh, please try the command again :D")
            return False

        prediction_number = None

        if message is None or len(message) < 0:
            bot.say(bad_command_message)
            return True

        try:
            prediction_number = int(message.split(" ")[0])
        except (KeyError, ValueError):
            bot.say(bad_command_message)
            return True

        if prediction_number < 0 or prediction_number > max_wins:
            bot.say(bad_command_message)
            return True

        with DBManager.create_session_scope() as db_session:
            # Get the current open prediction
            current_prediction_run = (
                db_session.query(PredictionRun).filter_by(ended=None, open=True, type=type).one_or_none()
            )
            if current_prediction_run is None:
                bot.say(
                    "{}, There is no {} run active that accepts predictions right now.".format(
                        source.username_raw, self.settings["challenge_name"]
                    )
                )
                return True

            user_entry = (
                db_session.query(PredictionRunEntry)
                .filter_by(prediction_run_id=current_prediction_run.id, user_id=source.id)
                .one_or_none()
            )
            if user_entry is not None:
                old_prediction_num = user_entry.prediction
                user_entry.prediction = prediction_number
                bot.say(
                    "{}, Updated your prediction for run {} from {} to {}".format(
                        source.username_raw, current_prediction_run.id, old_prediction_num, prediction_number
                    )
                )
            else:
                user_entry = PredictionRunEntry(current_prediction_run.id, source.id, prediction_number)
                db_session.add(user_entry)
                bot.say(
                    "{}, Your prediction for {} wins in run {} has been submitted.".format(
                        source.username_raw, prediction_number, current_prediction_run.id
                    )
                )

    @staticmethod
    def shared_new_predict(bot, source, type):
        with DBManager.create_session_scope() as db_session:
            # Check if there is already an open prediction
            current_prediction_run = (
                db_session.query(PredictionRun).filter_by(ended=None, open=True, type=type).one_or_none()
            )
            if current_prediction_run is not None:
                bot.say(
                    "{}, There is already a prediction run accepting submissions, close it before you can start a new run.".format(
                        source.username_raw
                    )
                )
                return True

            new_prediction_run = PredictionRun(type)
            db_session.add(new_prediction_run)
            db_session.commit()
            bot.say(
                "A new prediction run has been started, and is now accepting submissions. Prediction run ID: {}".format(
                    new_prediction_run.id
                )
            )

    @staticmethod
    def shared_end_predict(bot, source, type):
        with DBManager.create_session_scope() as db_session:
            # Check if there is a non-ended, but closed prediction run we can end
            predictions = db_session.query(PredictionRun).filter_by(ended=None, open=False, type=type).all()
            if len(predictions) == 0:
                bot.say("{}, There is no closed prediction runs we can end right now.".format(source.username_raw))
                return True

            for prediction in predictions:
                prediction.ended = utils.now()
            bot.say("Closed predictions with IDs {}".format(", ".join([str(p.id) for p in predictions])))

    @staticmethod
    def shared_close_predict(bot, source, type):
        with DBManager.create_session_scope() as db_session:
            # Check if there is a non-ended, but closed prediction run we can end
            current_prediction_run = (
                db_session.query(PredictionRun).filter_by(ended=None, open=True, type=type).one_or_none()
            )
            if current_prediction_run is None:
                bot.say("{}, There is no open prediction runs we can close right now.".format(source.username_raw))
                return True

            current_prediction_run.open = False
            bot.say(
                "{}, Predictions are no longer accepted for prediction run {}".format(
                    source.username_raw, current_prediction_run.id
                )
            )

    def predict(self, **options):
        bot = options["bot"]
        message = options["message"]
        source = options["source"]
        self.shared_predict(bot, source, message, 0)

    def mini_predict(self, **options):
        bot = options["bot"]
        message = options["message"]
        source = options["source"]
        self.shared_predict(bot, source, message, 1)

    def new_predict(self, **options):
        bot = options["bot"]
        source = options["source"]
        self.shared_new_predict(bot, source, 0)

    def mini_new_predict(self, **options):
        bot = options["bot"]
        source = options["source"]
        self.shared_new_predict(bot, source, 1)

    def end_predict(self, **options):
        bot = options["bot"]
        source = options["source"]
        self.shared_end_predict(bot, source, 0)

    def mini_end_predict(self, **options):
        bot = options["bot"]
        source = options["source"]
        self.shared_end_predict(bot, source, 1)

    def close_predict(self, **options):
        bot = options["bot"]
        source = options["source"]
        self.shared_close_predict(bot, source, 0)

    def mini_close_predict(self, **options):
        bot = options["bot"]
        source = options["source"]
        self.shared_close_predict(bot, source, 1)

import logging
import datetime

from pajbot.modules import BaseModule
from pajbot.models.db import DBManager, Base
from pajbot.models.command import Command, CommandExample

import sqlalchemy
from sqlalchemy import orm
from sqlalchemy.orm import relationship, joinedload, backref
from sqlalchemy import Column, Integer, Boolean, DateTime, ForeignKey, String
from sqlalchemy.dialects.mysql import TEXT

log = logging.getLogger(__name__)

class PredictionRun(Base):
    __tablename__ = 'tb_prediction_run'

    id = Column(Integer, primary_key=True)
    winner_id = Column(Integer, nullable=True)
    started = Column(DateTime, nullable=False)
    ended = Column(DateTime, nullable=True)
    open = Column(Boolean,
            nullable=False,
            default=True,
            server_default=sqlalchemy.sql.expression.true())

    def __init__(self):
        self.id = None
        self.winner_id = None
        self.started = datetime.datetime.now()
        self.ended = None

class PredictionRunEntry(Base):
    __tablename__ = 'tb_prediction_run_entry'

    id = Column(Integer, primary_key=True)
    prediction_run_id = Column(Integer, ForeignKey('tb_prediction_run.id'), nullable=False)
    user_id = Column(Integer, nullable=False)
    prediction = Column(Integer, nullable=False)

    user = relationship('User',
            cascade='',
            uselist=False,
            lazy='noload',
            foreign_keys='User.id',
            primaryjoin='User.id==PredictionRunEntry.user_id')

    def __init__(self, prediction_run_id, user_id, prediction):
        self.id = None
        self.prediction_run_id = prediction_run_id
        self.user_id = user_id
        self.prediction = prediction


class PredictModule(BaseModule):

    ID = __name__.split('.')[-1]
    NAME = 'Prediction module'
    DESCRIPTION = 'Handles predictions of arena wins'

    def load_commands(self, **options):
        self.commands['predict'] = Command.raw_command(self.predict,
                delay_all=0,
                delay_user=10,
                sub_only=True,
                can_execute_with_whisper=True,
                description='Predict how many wins will occur in the Arena challenge')
        self.commands['newpredict'] = Command.raw_command(self.new_predict,
                delay_all=10,
                delay_user=10,
                description='Starts a new 100in10 arena run',
                level=750)
        self.commands['endpredict'] = Command.raw_command(self.end_predict,
                delay_all=10,
                delay_user=10,
                description='Ends a 100in10 arena run',
                level=750)
        self.commands['closepredict'] = Command.raw_command(self.close_predict,
                delay_all=10,
                delay_user=10,
                description='Close submissions to the latest 100in10 arena run',
                level=750)

    def predict(self, **options):
        bot = options['bot']
        message = options['message']
        source = options['source']

        if source.id is None:
            log.warn('Source ID is NONE, attempting to salvage by commiting users to the database.')
            bot.users.commit()
            log.info('New ID is: {}'.format(source.id))

        prediction_number = None

        if message is None or len(message) < 0:
            # bot.whisper(source.username, 'Missing argument to !predict command. Usage: !predict 69 where 69 is a number between 0 and 120 (inclusive).')
            bot.say('{}, Missing argument to !predict command. Usage: !predict 69 where 69 is a number between 0 and 120 (inclusive).'.format(source.username_raw))
            return True

        try:
            prediction_number = int(message.split(' ')[0])
        except (KeyError, ValueError):
            # bot.whisper(source.username, 'Invalid argument to !predict command. Usage: !predict 69 where 69 is a number between 0 and 120 (inclusive).')
            bot.say('{}, Invalid argument to !predict command. Usage: !predict 69 where 69 is a number between 0 and 120 (inclusive).'.format(source.username_raw))
            return True

        if prediction_number < 0 or prediction_number > 120:
            # bot.whisper(source.username, 'Invalid argument to !predict command. The prediction must be a value between 0 and 120 (inclusive).')
            bot.say('{}, Invalid argument to !predict command. Usage: !predict 69 where 69 is a number between 0 and 120 (inclusive).'.format(source.username_raw))
            return True

        with DBManager.create_session_scope() as db_session:
            # Get the current open prediction
            current_prediction_run = db_session.query(PredictionRun).filter_by(ended=None, open=True).one_or_none()
            if current_prediction_run is None:
                # bot.whisper(source.username, 'There is no arena run active that accepts predictions right now.')
                bot.say('{}, There is no arena run active that accepts predictions right now.'.format(source.username_raw))
                return True

            user_entry = db_session.query(PredictionRunEntry).filter_by(prediction_run_id=current_prediction_run.id, user_id=source.id).one_or_none()
            if user_entry is not None:
                old_prediction_num = user_entry.prediction
                user_entry.prediction = prediction_number
                # bot.whisper(source.username, 'Updated your prediction for run {} from {} to {}'.format(
                #     current_prediction_run.id, old_prediction_num, prediction_number))
                bot.say('{}, Updated your prediction for run {} from {} to {}'.format(
                    source.username_raw, current_prediction_run.id, old_prediction_num, prediction_number))
            else:
                user_entry = PredictionRunEntry(current_prediction_run.id, source.id, prediction_number)
                db_session.add(user_entry)
                # bot.whisper(source.username, 'Your prediction for {} wins in run {} has been submitted.'.format(
                #     prediction_number, current_prediction_run.id))
                bot.say('{}, Your prediction for {} wins in run {} has been submitted.'.format(
                    source.username_raw, prediction_number, current_prediction_run.id))

    def new_predict(self, **options):
        bot = options['bot']
        source = options['source']

        with DBManager.create_session_scope() as db_session:
            # Check if there is already an open prediction
            current_prediction_run = db_session.query(PredictionRun).filter_by(ended=None, open=True).one_or_none()
            if current_prediction_run is not None:
                # bot.whisper(source.username, 'There is already a prediction run accepting submissions, use !closepredict to close submissions for that prediction.')
                bot.say('{}, There is already a prediction run accepting submissions, use !closepredict to close submissions for that prediction.'.format(source.username_raw))
                return True

            new_prediction_run = PredictionRun()
            db_session.add(new_prediction_run)
            db_session.commit()
            # bot.whisper(source.username, 'A new prediction run has been started, and is now accepting submissions. Prediction run ID: {}'.format(new_prediction_run.id))
            bot.say('A new prediction run has been started, and is now accepting submissions. Prediction run ID: {}'.format(new_prediction_run.id))

    def end_predict(self, **options):
        bot = options['bot']
        source = options['source']

        with DBManager.create_session_scope() as db_session:
            # Check if there is a non-ended, but closed prediction run we can end
            current_prediction_run = db_session.query(PredictionRun).filter_by(ended=None, open=False).one_or_none()
            if current_prediction_run is None:
                # bot.whisper(source.username, 'There is no closed prediction runs we can end right now.')
                bot.say('{}, There is no closed prediction runs we can end right now.'.format(source.username_raw))
                return True

            current_prediction_run.ended = datetime.datetime.now()
            # bot.whisper(source.username, 'Prediction run with ID {} has been closed.'.format(current_prediction_run.id))
            bot.say('Prediction run with ID {} has been closed.'.format(current_prediction_run.id))

    def close_predict(self, **options):
        bot = options['bot']
        source = options['source']

        with DBManager.create_session_scope() as db_session:
            # Check if there is a non-ended, but closed prediction run we can end
            current_prediction_run = db_session.query(PredictionRun).filter_by(ended=None, open=True).one_or_none()
            if current_prediction_run is None:
                # bot.whisper(source.username, 'There is no open prediction runs we can close right now.')
                bot.say('{}, There is no open prediction runs we can close right now.'.format(source.username_raw))
                return True

            current_prediction_run.open = False
            # bot.whisper(source.username, 'Predictions are no longer accepted for prediction run {}'.format(current_prediction_run.id))
            bot.say('{}, Predictions are no longer accepted for prediction run {}'.format(source.username_raw, current_prediction_run.id))

import json
import logging

from sqlalchemy import Boolean
from sqlalchemy import Column
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy.dialects.mysql import TEXT
from sqlalchemy.orm import reconstructor

from pajbot.managers import Base
from pajbot.managers import DBManager
from pajbot.models.action import ActionParser
from pajbot.tbutil import find

log = logging.getLogger('pajbot')


class Timer(Base):
    __tablename__ = 'tb_timer'

    id = Column(Integer, primary_key=True)
    name = Column(String(256), nullable=False)
    action_json = Column('action', TEXT, nullable=False)
    interval_online = Column(Integer, nullable=False)
    interval_offline = Column(Integer, nullable=False)
    enabled = Column(Boolean, nullable=False, default=True)

    def __init__(self, **options):
        self.id = None
        self.name = '??'
        self.action_json = '{}'
        self.interval_online = 5
        self.interval_offline = 30
        self.enabled = True

        self.refresh_tts()

        self.set(**options)

    def set(self, **options):
        self.name = options.get('name', self.name)
        log.debug(options)
        if 'action' in options:
            log.info('new action!')
            self.action_json = json.dumps(options['action'])
            self.action = ActionParser.parse(self.action_json)
        self.interval_online = options.get('interval_online', self.interval_online)
        self.interval_offline = options.get('interval_offline', self.interval_offline)
        self.enabled = options.get('enabled', self.enabled)

    @reconstructor
    def init_on_load(self):
        self.action = ActionParser.parse(self.action_json)

        self.refresh_tts()

    def refresh_tts(self):
        self.time_to_send_online = self.interval_online
        self.time_to_send_offline = self.interval_offline

    def refresh_action(self):
        self.action = ActionParser.parse(self.action_json)

    def run(self, bot):
        self.action.run(bot, source=None, message=None)


class TimerManager:
    def __init__(self, bot):
        self.bot = bot

        self.bot.execute_every(60, self.tick)

        if self.bot:
            self.bot.socket_manager.add_handler('timer.update', self.on_timer_update)
            self.bot.socket_manager.add_handler('timer.remove', self.on_timer_remove)

    def on_timer_update(self, data, conn):
        try:
            timer_id = int(data['timer_id'])
        except (KeyError, ValueError):
            log.warn('No timer ID found in on_timer_update')
            return False

        updated_timer = find(lambda timer: timer.id == timer_id, self.timers)
        if updated_timer:
            with DBManager.create_session_scope(expire_on_commit=False) as db_session:
                db_session.add(updated_timer)
                db_session.refresh(updated_timer)
                updated_timer.refresh_action()
                db_session.expunge(updated_timer)
        else:
            with DBManager.create_session_scope(expire_on_commit=False) as db_session:
                updated_timer = db_session.query(Timer).filter_by(id=timer_id).one_or_none()

        # Add the updated timer to the timer lists if required
        if updated_timer:
            if updated_timer not in self.timers:
                self.timers.append(updated_timer)
            if updated_timer not in self.online_timers and updated_timer.interval_online > 0:
                self.online_timers.append(updated_timer)
                updated_timer.refresh_tts()
            if updated_timer not in self.offline_timers and updated_timer.interval_offline > 0:
                self.offline_timers.append(updated_timer)
                updated_timer.refresh_tts()

        for timer in self.online_timers:
            if timer.enabled is False or timer.interval_online <= 0:
                self.online_timers.remove(timer)

        for timer in self.offline_timers:
            if timer.enabled is False or timer.interval_offline <= 0:
                self.offline_timers.remove(timer)

    def on_timer_remove(self, data, conn):
        try:
            timer_id = int(data['timer_id'])
        except (KeyError, ValueError):
            log.warn('No timer ID found in on_timer_update')
            return False

        removed_timer = find(lambda timer: timer.id == timer_id, self.timers)
        if removed_timer:
            if removed_timer in self.timers:
                self.timers.remove(removed_timer)
            if removed_timer in self.online_timers:
                self.online_timers.remove(removed_timer)
            if removed_timer in self.offline_timers:
                self.offline_timers.remove(removed_timer)

    def tick(self):
        if self.bot.is_online:
            for timer in self.online_timers:
                timer.time_to_send_online -= 1
            timer = find(lambda timer: timer.time_to_send_online <= 0, self.online_timers)
            if timer:
                timer.run(self.bot)
                timer.time_to_send_online = timer.interval_online
                self.online_timers.remove(timer)
                self.online_timers.append(timer)
        else:
            for timer in self.offline_timers:
                timer.time_to_send_offline -= 1
            timer = find(lambda timer: timer.time_to_send_offline <= 0, self.offline_timers)
            if timer:
                timer.run(self.bot)
                timer.time_to_send_offline = timer.interval_offline
                self.offline_timers.remove(timer)
                self.offline_timers.append(timer)

    def redistribute_timers(self):
        for x in range(0, len(self.offline_timers)):
            timer = self.offline_timers[x]
            timer.time_to_send_offline = timer.interval_offline * ((x + 1) / len(self.offline_timers))

        for x in range(0, len(self.online_timers)):
            timer = self.online_timers[x]
            timer.time_to_send_online = timer.interval_online * ((x + 1) / len(self.online_timers))

    def load(self):
        self.timers = []
        with DBManager.create_session_scope(expire_on_commit=False) as db_session:
            self.timers = db_session.query(Timer).order_by(Timer.interval_online, Timer.interval_offline, Timer.name).all()
            db_session.expunge_all()

        self.online_timers = [timer for timer in self.timers if timer.interval_online > 0 and timer.enabled]
        self.offline_timers = [timer for timer in self.timers if timer.interval_offline > 0 and timer.enabled]

        self.redistribute_timers()

        log.info('Loaded {} timers ({} online/{} offline)'.format(len(self.timers), len(self.online_timers), len(self.offline_timers)))
        return self

import logging

from tyggbot.models.db import DBManager, Base

from sqlalchemy import Column, Integer, String, Boolean

log = logging.getLogger('tyggbot')


class MOTD(Base):
    __tablename__ = 'tb_motd'

    id = Column(Integer, primary_key=True)
    message = Column(String(400))
    enabled = Column(Boolean)


class MOTDManager:
    def __init__(self, bot):
        self.db_session = DBManager.create_session()
        self.messages = []
        self.bot = bot
        self.minute = 0
        self.iterator = 0

        self.bot.execute_every(60, self.tick)

    def tick(self):
        if len(self.messages) == 0:
            # No MOTD messages
            return

        self.minute += 1
        interval = self.bot.settings['motd_interval_online'] if self.bot.is_online else self.bot.settings['motd_interval_offline']
        if self.minute >= interval:
            self.cycle()

    def cycle(self):
        if len(self.messages) == 0:
            # No MOTD messages
            return

        self.bot.say(self.messages[self.iterator % len(self.messages)])
        self.minute = 0
        self.iterator += 1

    def commit(self):
        self.db_session.commit()

    def reload(self):
        self.messages = []
        for motd in self.db_session.query(MOTD).filter_by(enabled=True):
            self.messages.append(motd.message)

        log.info('Loaded {0} MOTD messages'.format(len(self.messages)))
        return self

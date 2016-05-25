import json
import logging
import random
import threading
import time
from queue import Queue

import requests
from sqlalchemy import Boolean
from sqlalchemy import Column
from sqlalchemy import String

from pajbot.managers.connection import CustomServerConnection
from pajbot.managers.db import Base
from pajbot.managers.db import DBManager

log = logging.getLogger('pajbot')


class WhisperAccount(Base):
    __tablename__ = 'tb_whisper_account'

    username = Column(String(128), primary_key=True)
    oauth = Column(String(128))
    enabled = Column(Boolean)


class Whisper:
    def __init__(self, target, message):
        self.target = target
        self.message = message


class WhisperConnection:
    def __init__(self, conn, name, oauth, can_send_whispers=True):
        self.conn = conn
        self.num_msgs_sent = 0
        self.name = name
        self.oauth = oauth
        self.can_send_whispers = can_send_whispers

    def reduce_msgs_sent(self):
        self.num_msgs_sent -= 1


class WhisperConnectionManager:
    def __init__(self, reactor, bot, target, message_limit, time_interval, num_of_conns=30):
        self.db_session = DBManager.create_session()
        self.reactor = reactor
        self.bot = bot
        self.message_limit = message_limit
        self.time_interval = time_interval
        self.num_of_conns = num_of_conns
        self.whisper_thread = None

        self.connlist = []
        self.whispers = Queue()

        self.maintenance_lock = False

    def __contains__(self, connection):
        return connection in [c.conn for c in self.connlist]

    def start(self, accounts=[]):
        log.debug('Starting connection manager')
        try:
            # Update available group servers.
            # This will also be run at an interval to make sure it's up to date
            self.update_servers_list()
            self.reactor.execute_every(3600, self.update_servers_list)

            # Run the maintenance function every 4 seconds.
            # The maintenance function is responsible for reconnecting lost connections.
            self.reactor.execute_every(4, self.run_maintenance)

            # Fetch additional whisper accounts from the database
            for account in self.db_session.query(WhisperAccount).filter_by(enabled=True):
                account_data = {
                        'username': account.username,
                        'oauth': account.oauth
                        }
                accounts.append(account_data)

            # Start the connections.
            t = threading.Thread(target=self.start_connections, args=[accounts], name='WhisperConnectionStarterThread')
            t.daemon = True
            t.start()

            return True
        except:
            log.exception('WhisperConnectionManager: Unhandled exception')
            return False

    def start_connections(self, accounts):
        for account in accounts:
            newconn = self.make_new_connection(account['username'], account['oauth'], account.get('can_send_whispers', True))
            self.connlist.append(newconn)

        self.whisper_thread = threading.Thread(target=self.whisper_sender, name='WhisperThread')  # start a loop sending whispers in a thread
        self.whisper_thread.daemon = True
        self.whisper_thread.start()

    def quit(self):
        for connection in self.connlist:
            connection.conn.quit('bye')

    def update_servers_list(self):
        log.debug('Refreshing list of whisper servers')
        servers_list = json.loads(requests.get('http://tmi.twitch.tv/servers?cluster=group').text)
        self.servers_list = servers_list['servers']

    def whisper_sender(self):
        while True:
            try:
                whisp = self.whispers.get()
                username = whisp.target
                message = whisp.message

                valid_connection = None
                while valid_connection is None:
                    random_connection = random.choice(self.connlist)
                    if random_connection.conn.is_connected() and random_connection.num_msgs_sent < self.message_limit and random_connection.can_send_whispers is True:
                        valid_connection = random_connection
                    else:
                        time.sleep(0.1)

                log.debug('Sending whisper to {0} from {2}: {1}'.format(username, message, valid_connection.name))
                valid_connection.conn.privmsg('#jtv', '/w {0} {1}'.format(username, message))
                valid_connection.num_msgs_sent += 1
                valid_connection.conn.execute_delayed(self.time_interval, valid_connection.reduce_msgs_sent)
            except:
                log.exception('Caught an exception in the whisper_sender function')

    def run_maintenance(self):
        if self.maintenance_lock:
            return

        self.maintenance_lock = True
        for connection in self.connlist:
            if not connection.conn.is_connected():
                connection.conn.close()
                self.connlist.remove(connection)
                newconn = self.make_new_connection(connection.name, connection.oauth, connection.can_send_whispers)
                self.connlist.append(newconn)

        self.maintenance_lock = False

    def get_main_conn(self):
        for connection in self.connlist:
            if connection.conn.is_connected():
                return connection.conn

        log.error('No connection with is_connected() found in WhisperConnectionManager')

    def make_new_connection(self, name, oauth, can_send_whispers=True):
        server = random.choice(self.servers_list)
        ip, port = server.split(':')
        port = int(port)
        log.debug('Whispers: Connecting to server {0}'.format(server))

        newconn = CustomServerConnection(self.reactor)
        with self.reactor.mutex:
            self.reactor.connections.append(newconn)
        newconn.connect(ip, port, name, oauth, name)
        newconn.cap('REQ', 'twitch.tv/commands')

        # For debugging purposes
        newconn.cap('REQ', 'twitch.tv/membership')
        newconn.cap('REQ', 'twitch.tv/tags')

        return WhisperConnection(newconn, name, oauth, can_send_whispers)

    def on_disconnect(self, conn):
        log.debug('Whispers: Disconnected from server {} Reconnecting'.format(conn))
        conn.reconnect()
        conn.cap('REQ', 'twitch.tv/commands')
        conn.cap('REQ', 'twitch.tv/tags')
        conn.cap('REQ', 'twitch.tv/membership')
        return

    def whisper(self, target, message):
        if not target:
            target = self.target
        self.whispers.put(Whisper(target, message))

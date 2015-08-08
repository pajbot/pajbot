import random
import requests
from queue import Queue
import threading
import json
import pymysql

import logging

log = logging.getLogger('tyggbot')


class Whisper:
    def __init__(self, target, message):
        self.target = target
        self.message = message


class WhisperConnection:
    def __init__(self, conn, name, oauth):
        self.conn = conn
        self.num_msgs_sent = 0
        self.name = name
        self.oauth = oauth

        return

    def reduce_msgs_sent(self):
        self.num_msgs_sent -= 1


class WhisperConnectionManager:
    def __init__(self, reactor, tyggbot, target, message_limit, time_interval, num_of_conns=10):
        self.reactor = reactor
        self.tyggbot = tyggbot
        self.message_limit = message_limit
        self.time_interval = time_interval
        self.num_of_conns = num_of_conns

        self.connlist = []
        self.whispers = Queue()

    def __contains__(self, connection):
        return connection in [connection.conn for c in self.connlist]

    def start(self):
        log.debug("Starting connection manager")
        try:
            self.update_servers_list()
            self.reactor.execute_every(3600, self.update_servers_list)

            self.tyggbot.sqlconn.ping()
            cursor = self.tyggbot.sqlconn.cursor(pymysql.cursors.DictCursor)
            cursor.execute("SELECT name, oauth FROM tb_whisper_accs LIMIT %s", self.num_of_conns)
            for row in cursor:
                newconn = self.make_new_connection(row['name'], row['oauth'])
                self.connlist.append(newconn)

            self.reactor.execute_every(4, self.run_maintenance)
            t = threading.Thread(target=self.whisper_sender)  # start a loop sending whispers in a thread
            t.daemon = True
            t.start()
            return True
        except:
            log.exception("WhisperConnectionManager: Unhandled exception")
            return False

    def quit(self):
        for connection in self.connlist:
            connection.conn.quit('bye')

    def update_servers_list(self):
            log.debug("Getting a list of whisper servers")
            servers_list = json.loads(requests.get("http://tmi.twitch.tv/servers?cluster=group").text)
            self.servers_list = servers_list['servers']

    def whisper_sender(self):
        while True:
            whisp = self.whispers.get()
            username = whisp.target
            message = whisp.message

            i = 0
            while((not self.connlist[i].conn.is_connected()) or self.connlist[i].num_msgs_sent >= self.message_limit):
                i += 1  # find a usable connection
                if i >= len(self.connlist):
                    i = 0

            log.debug('Sending whisper: {0} {1}'.format(username, message))
            self.connlist[i].conn.privmsg('#jtv', '/w {0} {1}'.format(username, message))
            self.connlist[i].num_msgs_sent += 1
            self.connlist[i].conn.execute_delayed(self.time_interval, self.connlist[i].reduce_msgs_sent)

    def run_maintenance(self):
        for connection in self.connlist:
            if not connection.conn.is_connected():
                connection.conn.close()
                self.connlist.remove(connection)
                newconn = self.make_new_connection(connection.name, connection.oauth)
                self.connlist.append(newconn)

    def get_main_conn(self):
        for connection in self.connlist:
            if connection.conn.is_connected():
                return connection.conn

        log.error("No connection with is_connected() found")

    def make_new_connection(self, name, oauth):
        server = random.choice(self.servers_list)
        ip, port = server.split(':')
        port = int(port)
        log.debug("Whispers: Connection to server {0}".format(server))

        newconn = self.reactor.server().connect(ip, port, name, oauth, name)
        newconn.cap('REQ', 'twitch.tv/commands')
        return WhisperConnection(newconn, name, oauth)

    def on_disconnect(self, conn):
        conn.reconnect()
        return

    def whisper(self, target, message):
        if not target:
            target = self.target
        self.whispers.put(Whisper(target, message))

import irc
import random
import requests
import queue
import threading

import logging

log = logging.getLogger('tyggbot')

class Whisper:
    def __init__(self, target, message):
        self.target = target
        self.message = message


class WhisperConnection:
    def __init__(self, conn):
        self.conn = conn
        self.num_msgs_sent = 0

        return

    def reduce_msgs_sent(self):
        self.num_msgs_sent -= 1


class WhisperConnectionManager:
    def __init__(self, reactor, tyggbot, message_limit, time_interval, num_of_conns):
        self.reactor = reactor
        self.tyggbot = tyggbot
        self.message_limit = message_limit
        self.time_interval = time_interval
        self.num_of_conns = num_of_conns

        self.connlist = []
        self.whispers = Queue()

    def start(self):
        log.debug("Starting connection manager")
        try:
            self.tyggbot.sqlconn.ping()
            cursor = self.tyggbot.sqlconn.cursor(pymysql.cursors.DictCursor)
            cursor.execute("SELECT name, oauth FROM tb_whisper_accs LIMIT %s", self.num_of_conns)
            for row in cursor:
                newconn = self.make_new_connection(row['name'], row['oauth'])
                self.connlist.append(newconn)

            self.reactor.execute_every(4, self.run_maintenance)
            t = threading.Thread(target=self.whisper_sender) # start a loop sending whispers in a thread
            t.daemon = True
            t.start()
            return True
        except:
            log.exception("WhisperConnectionManager: Unhandled exception")
            return False

    def whisper_sender(self):
        while True:
            whisp = self.whispers.get()
            i = 0
            while((not self.connlist[i].conn.is_connected()) or self.connlist[i].num_msgs_sent >= self.message_limit):
                i += 1  # find a usable connection
            log.debug('Sending whisper: {0} {1}'.format(username, message))
            self.connlist[i].conn.privmsg('#jtv', '/w {0} {1}'.format(username, message))
            self.connlist[i].num_msgs_sent += 1
            self.connlist[i].execute_in(self.time_interval, self.connlist[i].reduce_msgs_sent)

    def run_maintenance(self):
        for connection in self.connlist:
            if not connection.conn.is_connected():
                connection.conn.reconnect()


    def get_main_conn(self):
        for connection in self.connlist:
            if connection.conn.is_connected():
                return connection.conn

        log.error("No connection with is_connected() found")

    def make_new_connection(self, name, oauth):
        servers_list = json.loads(requests.get("http://tmi.twitch.tv/servers?cluster=group").text)
        server = random.choice(servers_list['servers'])
        ip, port = server.split(':')
        port = int(port)
        log.debug("Whispers: Connection to server {0}", server)

        newconn = self.reactor.server().connect(ip, port, name, oauth, name)
        newconn.cap('REQ', 'twitch.tv/commands')
        return Connection(newconn)
        

    def on_disconnect(self, conn):
        conn.reconnect()
        return

    def whisper(self, target, message):
        self.whispers.put(Whisper(target, message))

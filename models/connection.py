import irc
import random

import logging

log = logging.getLogger('tyggbot')


class Connection:
    def __init__(self, conn):
        self.conn = conn
        self.num_msgs_sent = 0
        self.in_channel = False

        return

    def reduce_msgs_sent(self):
        self.num_msgs_sent -= 1


class ConnectionManager:
    def __init__(self, reactor, tyggbot, message_limit):
        self.backup_conns_number = 2

        self.reactor = reactor
        self.tyggbot = tyggbot
        self.message_limit = message_limit

        self.connlist = []

    def start(self):
        log.debug("Starting connection manager")
        try:
            for i in range(0, self.backup_conns_number + 1):
                newconn = self.make_new_connection()
                self.connlist.append(newconn)

            self.get_main_conn()

            if self.tyggbot.phrases['welcome']:
                phrase_data = {
                    'nickname': self.tyggbot.nickname,
                    'version': self.tyggbot.version,
                     }

            self.tyggbot.say(self.tyggbot.phrases['welcome'].format(**phrase_data))

            self.reactor.execute_every(4, self.run_maintenance)
            return True
        except:
            return False

    def run_maintenance(self):
        clean_conns_count = 0
        tmp = []  # new list of connections
        for connection in self.connlist:
            if not connection.conn.is_connected():
                log.debug("Removing connection because not connected")
                continue  # don't want this connection in the new list

            if connection.num_msgs_sent == 0:
                if clean_conns_count >= self.backup_conns_number:  # we have more connections than needed
                    log.debug("Removing connection because we have enough backup")
                    connection.conn.close()
                    continue  # don't want this connection
                else:
                    clean_conns_count += 1

            tmp.append(connection)

        self.connlist = tmp  # replace the old list with the newly constructed one
        need_more = self.backup_conns_number - clean_conns_count

        for i in range(0, need_more):  # add as many fresh connections as needed
            newconn = self.make_new_connection()
            self.connlist.append(newconn)

        self.get_main_conn()

    def get_main_conn(self):
        for connection in self.connlist:
            if connection.conn.is_connected():
                if not connection.in_channel:
                    if irc.client.is_channel(self.tyggbot.channel):
                        connection.conn.join(self.tyggbot.channel)
                        log.debug("Joined channel")
                        connection.in_channel = True

                return connection.conn

        log.error("No connection with is_connected() found")

    def make_new_connection(self):
        log.debug("Creating a new IRC connection...")
        log.debug('Fetching random IRC server...')
        data = self.tyggbot.twitchapi.get(['channels', self.tyggbot.streamer, 'chat_properties'])
        if data and len(data['chat_servers']) > 0:
            server = random.choice(data['chat_servers'])
            ip, port = server.split(':')
            port = int(port)

            log.debug('Fetched {0}:{1}'.format(ip, port))

            try:
                newconn = self.reactor.server().connect(ip, port, self.tyggbot.nickname, self.tyggbot.password, self.tyggbot.nickname)
                log.debug('Connecting to IRC server...')
                newconn.cap('REQ', 'twitch.tv/membership')
                newconn.cap('REQ', 'twitch.tv/commands')
                newconn.cap('REQ', 'twitch.tv/tags')

                connection = Connection(newconn)
                return connection
            except irc.client.ServerConnectionError:
                return

        else:
            log.error("No proper data returned when fetching IRC servers")
            return None

    def on_disconnect(self, chatconn):
        self.run_maintenance()
        return

    def privmsg(self, channel, message):
        i = 0
        while((not self.connlist[i].conn.is_connected()) or self.connlist[i].num_msgs_sent >= self.message_limit):
            i += 1  # find a usable connection

        self.connlist[i].num_msgs_sent += 1
        self.connlist[i].conn.privmsg(channel, message)
        self.reactor.execute_delayed(31, self.connlist[i].reduce_msgs_sent)

        if self.connlist[i].num_msgs_sent >= self.message_limit:
            self.run_maintenance()

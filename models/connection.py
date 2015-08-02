import from llist import dllist, dllistnode
import irc
import random

import logging

log = logging.getLogger() 

class Connection:
    def __init__(self, conn):
        self.conn = conn
        self.num_msgs_sent = 0
        
        return

class ConnectionManager:
    def __init__(self, reactor, tyggbot, message_limit):
        self.backup_conns_number = 2

        self.reactor = reactor
        self.tyggbot = tyggbot
        self.message_limit = message_limit

        self.connlist = dllist()

    def start(self):
        for i in range(0, backup_conns_number):
            newconn = self.make_new_connection()
            self.connlist.append(newconn)

    def make_new_connection(self):
        log.debug("Creating a new IRC connection...")
        log.debug('Fetching random IRC server...')
        data = self.twitchapi.get(['channels', self.tyggbot.streamer, 'chat_properties'])
        if data and len(data['chat_servers']) > 0:
            server = random.choice(data['chat_servers'])
            ip, port = server.split(':')
            port = int(port)

            log.debug('Fetched {0}:{1}'.format(ip, port))

            try:
                newconn = self.reactor.server().connect(self, ip, port, self.tyggbot.nickname, self.tyggbot.password, self.tyggbot.nickname)
                newconn.cap('REQ', 'twitch.tv/membership')
                newconn.cap('REQ', 'twitch.tv/commands')
                newconn.cap('REQ', 'twitch.tv/tags')

                connection = Connection(newconn)
                return connection
            except irc.client.ServerConnectionError:
                pass
        log.debug('Connecting to IRC server...')


        else:
            log.error("No proper data returned when fetching IRC servers")
            return None

    def on_disconnect(self, chatconn):
        chatconn.reconnect()
        return

    def privmsg(self, channel, message):
        return

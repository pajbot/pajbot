import logging
import random

from apiwrappers import ChatDepotAPI

import irc.client

class WhisperConn(irc.client.SimpleIRCClient):
    def __init__(self, target, nickname, password, reactor):
        irc.client.SimpleIRCClient.__init__(self)

        self.reactor = reactor

        self.log = logging.getLogger('tyggbot')

        self.log.debug('WHISPER')
        self.log.debug(self.reactor)

        self.target = target
        self.nickname = nickname
        self.password = password
        self.reconnection_interval = 5

        self.connection.set_keepalive(60)
        self.connection.execute_every(5, self.whisper, ('pajlada', 'hello'))

        self.connection.execute_delayed(2, self.whisper, ('pajlada', 'asdadsasd'))

        self.ip = '199.9.253.119'
        self.port = 6667

        data = ChatDepotAPI().get(['room_memberships'], {'oauth_token': self.password.split(':')[1]})
        if data:
            room = data['memberships'][0]['room']

            if room:
                server = random.choice([server for server in room['servers'] if '6667' in server])
                self.ip, self.port = server.split(':')
                self.port = int(self.port)

    def whisper(self, username, message):
        self.log.debug('Sending whisper: {0} {1}'.format(username, message))
        self.privmsg('#jtv', '/w {0} {1}'.format(username, message))

    def privmsg(self, target, message):
        try:
            if not target:
                target = self.target

            self.connection.privmsg(target, message)
        except Exception as e:
            self.log.error('Exception caught while sending privmsg: {0}'.format(e))

    def on_welcome(self, chatconn, event):
        self.log.debug('Connected to Whisper server.')

    def _connected_checker(self):
        if not self.connection.is_connected():
            self.connection.execute_delayed(self.reconnection_interval,
                                            self._connected_checker)
            self.connect()

    def connect(self):
        self.log.debug('Connecting to Whisper server... ({0} {1})'.format(self.ip, self.port))
        self.connection.execute_delayed(2, self.whisper, ('pajlada', 'asdadsasd'))
        try:
            irc.client.SimpleIRCClient.connect(self, self.ip, self.port, self.nickname, self.password, self.nickname)
        except irc.client.ServerConnectionError:
            pass

    def on_disconnect(self, chatconn, event):
        self.log.debug('Disconnecting from Whisper server')
        self.connection.execute_delayed(self.reconnection_interval,
                                        self._connected_checker)

    def quit(self):
        self.connection.quit("bye")

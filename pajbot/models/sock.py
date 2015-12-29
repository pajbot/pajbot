import os
import socket
import logging
import threading
import json

log = logging.getLogger(__name__)

class SocketResource:
    def __init__(self, socket_file):
        self.socket_file = socket_file
        try:
            os.remove(self.socket_file)
        except OSError:
            pass
        self.server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.server.bind(self.socket_file)
        self.server.listen(5)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.server.close()
        try:
            os.remove(self.socket_file)
        except OSError:
            pass

class SocketManager:
    def __init__(self, bot):
        self.handlers = {}
        self.socket_file = None

        if self.check_config(bot.config) is True:
            self.socket_file = bot.config['sock']['sock_file']
            self.thread = threading.Thread(target=self.start, name='SocketManagerThread')
            self.thread.daemon = True
            self.thread.start()

    def quit(self):
        if self.socket_file is not None:
            try:
                os.remove(self.socket_file)
            except OSError:
                pass

    def check_config(self, config):
        if 'sock' not in config:
            log.warn('Missing [sock] section in config file for SocketManager to start.')
            return False

        if 'sock_file' not in config['sock']:
            log.warn('Missing sock_file value in [sock] section in config file for SocketManager to start.')
            return False

        return True

    def add_handler(self, handler, method):
        log.debug('Added a handler to the SocketManager')
        if handler not in self.handlers:
            self.handlers[handler] = [method]
        else:
            self.handlers[handler].append(method)

    def start(self):
        with SocketResource(self.socket_file) as sr:
            while True:
                conn, addr = sr.server.accept()
                log.debug('Accepted connection from {}'.format(addr))

                data = conn.recv(4096)
                if data:
                    try:
                        json_data = json.loads(data.decode('utf-8'))
                    except ValueError:
                        log.warn('Invalid JSON Data passwed through SocketManager: {}'.format(data))
                        continue

                    if 'event' not in json_data:
                        log.warn('Missing event key from json data: {}'.format(json_data))
                        continue

                    if 'data' not in json_data:
                        log.warn('Missing data key in json_data: {}'.format(json_data))
                        continue

                    try:
                        event = json_data['event'].lower()
                    except AttributeError:
                        log.warn('Unknown event: {}'.format(json_data['event']))
                        continue

                    try:
                        handler, trigger = json_data['event'].lower().split('.')
                    except ValueError:
                        log.warn('Missing separator in event: {}'.format(json_data))
                        continue

                    if event in self.handlers:
                        for handler in self.handlers[event]:
                            handler(json_data['data'], conn)
                    else:
                        log.debug('Unhandled handler: {}'.format(event))

class SocketClientManager:
    sock_file = None

    def init(sock_file):
        SocketClientManager.sock_file = sock_file

    def send(event, data):
        if SocketClientManager.sock_file is None:
            return False

        payload = {
                'event': event,
                'data': data
                }

        payload_bytes = json.dumps(payload).encode('utf-8')

        try:
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
                client.connect(SocketClientManager.sock_file)
                client.sendall(payload_bytes)
                return True
        except (socket.error, socket.herror, socket.gaierror):
            log.exception('A socket error occured')
            return False
        except socket.timeout:
            log.exception('The server took to long to respond.')
            return False

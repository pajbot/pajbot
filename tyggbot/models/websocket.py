import json
import logging
import threading

log = logging.getLogger('tyggbot')


class WebSocketServer:
    clients = []

    def __init__(self, manager, port, secure=False, key_path=None, crt_path=None):
        self.manager = manager
        from twisted.internet import reactor, ssl

        from autobahn.twisted.websocket import WebSocketServerFactory, \
                WebSocketServerProtocol

        class MyServerProtocol(WebSocketServerProtocol):
            def onConnect(self, request):
                log.info(self.factory)
                log.info('Client connecting: {0}'.format(request.peer))

            def onOpen(self):
                log.info('WebSocket connection open. {0}'.format(self))
                WebSocketServer.clients.append(self)

            def onMessage(self, payload, isBinary):
                if isBinary:
                    log.info('Binary message received: {0} bytes'.format(len(payload)))
                else:
                    log.info('Text message received: {0}'.format(payload.decode('utf8')))

            def onClose(self, wasClean, code, reason):
                log.info('WebSocket connection closed: {0}'.format(reason))
                try:
                    WebSocketServer.clients.remove(self)
                except:
                    pass

        factory = WebSocketServerFactory()
        factory.protocol = MyServerProtocol

        def reactor_run(reactor, factory, port, context_factory=None):
            log.info(reactor)
            log.info(factory)
            log.info(port)
            if context_factory:
                log.info('wss secure')
                reactor.listenSSL(port, factory, context_factory)
            else:
                log.info('ws unsecure')
                reactor.listenTCP(port, factory)
            reactor.run(installSignalHandlers=0)

        if secure:
            context_factory = ssl.DefaultOpenSSLContextFactory(key_path, crt_path)
        else:
            context_factory = None

        reactor_thread = threading.Thread(target=reactor_run,
                args=(reactor,
                    factory,
                    port,
                    context_factory),
                name='WebSocketThread')
        reactor_thread.daemon = True
        reactor_thread.start()


class WebSocketManager:
    def __init__(self, bot):
        self.clients = []
        self.server = None
        self.bot = bot
        try:
            if 'websocket' in bot.config and bot.config['websocket']['enabled'] == '1':
                # Initialize twisted logging
                try:
                    from twisted.python import log as twisted_log
                    twisted_log.addObserver(WebSocketManager.on_log_message)
                except ImportError:
                    log.error('twisted is not installed, websocket cannot be initialized.')
                    return
                except:
                    log.exception('Uncaught exception')
                    return

                port = int(bot.config['websocket']['port'])
                secure = False
                key_path = None
                crt_path = None
                if 'ssl' in bot.config['websocket'] and bot.config['websocket']['ssl'] == '1':
                    secure = True
                    if 'key_path' in bot.config['websocket']:
                        key_path = bot.config['websocket']['key_path']
                    if 'crt_path' in bot.config['websocket']:
                        crt_path = bot.config['websocket']['crt_path']
                self.server = WebSocketServer(self, port, secure, key_path, crt_path)
        except:
            log.exception('Uncaught exception in WebSocketManager')

    def emit(self, event, data={}):
        if self.server:
            payload = json.dumps({
                'event': event,
                'data': data,
                }).encode('utf8')
            for client in self.server.clients:
                client.sendMessage(payload, False)

    def on_log_message(message, isError=False, printed=False):
        if isError:
            log.error(message['message'])
        else:
            log.debug(message['message'])

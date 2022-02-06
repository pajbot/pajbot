from typing import Any, List

import json
import logging
import threading
from pathlib import Path

log = logging.getLogger("pajbot")


class WebSocketServer:
    clients: List[Any] = []

    def __init__(self, manager, port, secure=False, key_path=None, crt_path=None, unix_socket_path=None):
        self.manager = manager
        from autobahn.twisted.websocket import WebSocketServerFactory, WebSocketServerProtocol
        from twisted.internet import reactor, ssl

        class MyServerProtocol(WebSocketServerProtocol):
            def onConnect(self, request):
                # log.info(self.factory)
                # log.info('Client connecting: {0}'.format(request.peer))
                pass

            def onOpen(self):
                log.info("WebSocket connection open")
                WebSocketServer.clients.append(self)

            def onMessage(self, payload, isBinary):
                if isBinary:
                    log.info(f"Binary message received: {len(payload)} bytes")
                else:
                    log.info(f"Text message received: {payload.decode('utf8')}")

            def onClose(self, wasClean, code, reason):
                log.info(f"WebSocket connection closed: {reason}")
                try:
                    WebSocketServer.clients.remove(self)
                except:
                    pass

        factory = WebSocketServerFactory()
        factory.setProtocolOptions(autoPingInterval=15, autoPingTimeout=5)
        factory.protocol = MyServerProtocol

        def reactor_run(reactor, factory, port, context_factory=None, unix_socket_path=None):
            if unix_socket_path:
                sock_file = Path(unix_socket_path)
                if sock_file.exists():
                    sock_file.unlink()
                reactor.listenUNIX(unix_socket_path, factory)
            else:
                if context_factory:
                    log.info("wss secure")
                    reactor.listenSSL(port, factory, context_factory)
                else:
                    log.info("ws unsecure")
                    reactor.listenTCP(port, factory)
            reactor.run(installSignalHandlers=0)

        if secure:
            context_factory = ssl.DefaultOpenSSLContextFactory(key_path, crt_path)
        else:
            context_factory = None

        reactor_thread = threading.Thread(
            target=reactor_run, args=(reactor, factory, port, context_factory, unix_socket_path), name="WebSocketThread"
        )
        reactor_thread.daemon = True
        reactor_thread.start()


class WebSocketManager:
    def __init__(self, bot):
        self.clients = []
        self.server = None
        self.bot = bot

        if "websocket" not in bot.config:
            log.debug(
                "WebSocket support not set up, check out https://github.com/pajbot/pajbot/wiki/Config-File#websocket"
            )
            return

        cfg = bot.config["websocket"]
        streamer = bot.streamer.login

        try:
            if cfg["enabled"] == "1":
                # Initialize twisted logging
                try:
                    from twisted.python import log as twisted_log

                    twisted_log.addObserver(WebSocketManager.on_log_message)
                except ImportError:
                    log.error("twisted is not installed, websocket cannot be initialized.")
                    return
                except:
                    log.exception("Uncaught exception")
                    return

                ssl = bool(cfg.get("ssl", "0") == "1")
                port = int(cfg.get("port", "443" if ssl else "80"))
                key_path = cfg.get("key_path", "")
                crt_path = cfg.get("crt_path", "")
                unix_socket_path = cfg.get("unix_socket", f"/var/run/pajbot/{streamer}/websocket.sock")

                if ssl:
                    if key_path == "" or crt_path == "":
                        log.error("SSL enabled in config, but missing key_path or crt_path")
                        return

                self.server = WebSocketServer(self, port, ssl, key_path, crt_path, unix_socket_path)
        except:
            log.exception("Uncaught exception in WebSocketManager")

    def emit(self, event, data={}):
        if self.server:
            payload = json.dumps({"event": event, "data": data}).encode("utf8")
            for client in self.server.clients:
                client.sendMessage(payload, False)

    @staticmethod
    def on_log_message(message, isError=False, printed=False):
        if isError:
            log.error(message["message"])
        else:
            pass
            # log.debug('on_log_message({})'.format(message['message']))

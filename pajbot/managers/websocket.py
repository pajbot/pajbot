import json
import logging
import threading
from pathlib import Path

from pajbot.managers.handler import HandlerManager
from pajbot.managers.db import DBManager

from pajbot.models.web_sockets import WebSocket

log = logging.getLogger("pajbot")


class WebSocketServer:
    clients = []

    def __init__(self, manager, port, secure=False, key_path=None, crt_path=None, unix_socket_path=None):
        self.manager = manager
        from twisted.internet import reactor, ssl

        from autobahn.twisted.websocket import WebSocketServerFactory, WebSocketServerProtocol

        class MyServerProtocol(WebSocketServerProtocol):
            def __init__(self):
                WebSocketServerProtocol.__init__(self)
                self.widget_id = ""

            def onConnect(self, request):
                pass

            def onOpen(self):
                log.info("WebSocket connection open")

            def onMessage(self, payload, isBinary):
                if isBinary:
                    log.info(f"Binary message received: {len(payload)} bytes")
                else:
                    with DBManager.create_session_scope() as db_session:
                        try:
                            message = json.loads(payload)
                        except:
                            self.sendClose()
                            return
                        switcher = {
                            "auth": self._auth,
                            "next_song": self._next_song,
                            "ready": self._ready,
                        }
                        if "event" in message and "data" in message and message["event"] in switcher and switcher[message["event"]](db_session, message["data"]):
                            pass
                        else:
                            self.sendClose()

            def onClose(self, wasClean, code, reason):
                log.info(f"WebSocket {self.widget_id} connection closed: {reason}")
                try:
                    WebSocketServer.clients.remove(self)
                except:
                    pass

            def _auth(self, db_session, data):
                if "salt" not in data:
                    return False
                ws = WebSocket._by_salt(db_session, data["salt"])
                if not ws:
                    return False
                self.widget_id = ws.widget_id
                WebSocketServer.clients.append(self)
                return True

            def _next_song(self, db_session, data):
                if "salt" not in data:
                    return False
                if not WebSocket._by_salt(db_session, data["salt"]):
                    return False
                manager.bot.songrequest_manager.load_song()
                return True

            def _ready(self, db_session, data):
                if "salt" not in data:
                    return False
                if not WebSocket._by_salt(db_session, data["salt"]):
                    return False
                manager.bot.songrequest_manager.ready()
                return True

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
                unix_socket_path = cfg.get("unix_socket", None)

                if ssl:
                    if key_path == "" or crt_path == "":
                        log.error("SSL enabled in config, but missing key_path or crt_path")
                        return

                self.server = WebSocketServer(self, port, ssl, key_path, crt_path, unix_socket_path)
        except:
            log.exception("Uncaught exception in WebSocketManager")

    def emit(self, event, widget_id=None, data={}):
        if self.server:
            payload = json.dumps({"event": event, "data": data}).encode("utf8")
            for client in self.server.clients:
                if not widget_id or client.widget_id == widget_id:
                    client.sendMessage(payload, False)

    @staticmethod
    def on_log_message(message, isError=False, printed=False):
        if isError:
            log.error(message["message"])
        else:
            pass
            # log.debug('on_log_message({})'.format(message['message']))

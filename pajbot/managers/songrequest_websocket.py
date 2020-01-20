import json
import logging
import threading
import time
from pathlib import Path

from twisted.internet import reactor
from autobahn.twisted.websocket import WebSocketServerFactory, WebSocketServerProtocol

from pajbot.models.songrequest import SongrequestQueue, SongrequestHistory
from pajbot.managers.handler import HandlerManager
from pajbot.managers.db import DBManager
import urllib

log = logging.getLogger("pajbot")
current_milli_time = lambda: int(round(time.time() * 1000))


def find_youtube_id_in_string(string):
    if len(string) < 11:
        # Too short to be a youtube ID
        return False

    if len(string) == 11:
        # Assume it's a straight up youtube ID
        return string

    if not (string.lower().startswith("http://") or string.lower().startswith("https://")):
        string = "http://" + string

    urldata = urllib.parse.urlparse(string)

    if urldata.netloc == "youtu.be":
        youtube_id = urldata.path[1:]
    elif urldata.netloc.endswith("youtube.com"):
        qs = urllib.parse.parse_qs(urldata.query)
        if "v" not in qs:
            return False
        youtube_id = qs["v"][0]
    else:
        return False

    return youtube_id


def find_youtube_video_by_search(search):
    try:
        query_string = urllib.parse.urlencode({"search_query": search})
        html_content = urllib.request.urlopen("http://www.youtube.com/results?" + query_string)
        return re.findall(r"href=\"\/watch\?v=(.{11})", html_content.read().decode())[0]
    except:
        return None


def isfloat(str):
    try:
        float(str)
    except ValueError:
        return False
    return True


def isint(str):
    try:
        int(str)
    except ValueError:
        return False
    return True


class SongRequestWebSocketServer:
    clients = []
    manager_ext = None

    def __init__(self, manager, port, secure=False, key_path=None, crt_path=None, unix_socket_path=None):
        self.manager = manager_ext = manager

        class MyServerProtocol(WebSocketServerProtocol):
            def __init__(self):
                self.isAuthed = False
                self.user_id = None
                self.user_name = None
                WebSocketServerProtocol.__init__(self)

            def onOpen(self):
                SongRequestWebSocketServer.clients.append(self)

            def onMessage(self, payload, isBinary):
                if manager_ext.bot.songrequest_manager.enabled:
                    with DBManager.create_session_scope() as db_session:
                        if not isBinary:
                            try:
                                json_msg = json.loads(payload)
                            except:
                                self._close_conn()
                                return
                            if "event" not in json_msg or "data" not in json_msg:
                                self._close_conn()
                                return
                            switcher = {
                                "AUTH": self._auth,
                                "PAUSE": self._pause,
                                "RESUME": self._resume,
                                "SEEK": self._seek,
                                "SKIP": self._skip,
                                "PREVIOUS": self._previous,
                                "VOLUME": self._volume,
                                "CLOSE": self._close,
                                "OPEN": self._open,
                                "PLAY": self._play,
                                "REQUEST": self._request,
                                "REPLAY": self._replay,
                                "REQUEUE": self._requeue,
                                "MOVE": self._move,
                                "REMOVE": self._remove,
                            }
                            method = switcher.get(json_msg["event"], None)
                            if not method or not method(db_session, json_msg["data"]):
                                self._close_conn()
                                return

            def onClose(self, wasClean, code, reason):
                try:
                    SongRequestWebSocketServer.clients.remove(self)
                except:
                    pass

            def _close_conn(self):
                self.sendClose()

            def _auth(self, db_session, data):
                access_token = data["access_token"]
                user = manager_ext.bot.twitch_v5_api.user_from_access_token(
                    access_token, manager_ext.bot.twitch_helix_api, db_session
                )
                if not user or user.level < 500:
                    return False
                self.isAuthed = True
                self.login = user.login
                self._dump_state(db_session)
                return True

            def _dump_state(self, db_session):
                current_song = SongrequestQueue._from_id(
                    db_session, manager_ext.bot.songrequest_manager.current_song_id
                )
                data = {
                    "event": "initialize",
                    "data": {
                        "currentSong": current_song.webjsonify() if current_song else None,
                        "playlist": SongrequestQueue._get_playlist(db_session, 15),
                        "history": SongrequestHistory._get_history(db_session, 15),
                        "paused": manager_ext.bot.songrequest_manager.paused,
                        "open": manager_ext.bot.songrequest_manager.module_opened,
                        "volume": manager_ext.bot.songrequest_manager.volume
                        * 100
                        * (1 / (manager_ext.bot.songrequest_manager.settings["volume_multiplier"] / 100)),
                    },
                }
                payload = json.dumps(data).encode("utf8")
                self.sendMessage(payload, False)

            def _pause(self, db_session, data):
                if not self.isAuthed:
                    return False
                return manager_ext.bot.songrequest_manager.pause_function()

            def _resume(self, db_session, data):
                if not self.isAuthed:
                    return False
                return manager_ext.bot.songrequest_manager.resume_function()

            def _seek(self, db_session, data):
                if not self.isAuthed or "seek_time" not in data or not isfloat(data["seek_time"]):
                    return False
                return manager_ext.bot.songrequest_manager.seek_function(float(data["seek_time"]))

            def _skip(self, db_session, data):
                if not self.isAuthed:
                    return False
                return manager_ext.bot.songrequest_manager.skip_function(self.login)

            def _previous(self, db_session, data):
                if not self.isAuthed:
                    return False
                return manager_ext.bot.songrequest_manager.previous_function(self.login)

            def _volume(self, db_session, data):
                if not self.isAuthed or "volume" not in data or not isfloat(data["volume"]):
                    return False
                return manager_ext.bot.songrequest_manager.volume_function(float(data["volume"]))

            def _close(self, db_session, data):
                if not self.isAuthed:
                    return False
                return manager_ext.bot.songrequest_manager.close_module_function()

            def _open(self, db_session, data):
                if not self.isAuthed:
                    return False
                return manager_ext.bot.songrequest_manager.close_module_function()

            def _play(self, db_session, data):
                if not self.isAuthed or "database_id" not in data or not isint(data["database_id"]):
                    return False
                return manager_ext.bot.songrequest_manager.play_function(int(data["database_id"]), self.login)

            def _request(self, db_session, data):
                if not self.isAuthed or "request" not in data:
                    return False
                youtube_id = find_youtube_id_in_string(data["request"])
                if youtube_id is False:
                    youtube_id = find_youtube_video_by_search(data["request"])
                    if youtube_id is None:
                        return True
                return manager_ext.bot.songrequest_manager.request_function(youtube_id, self.login)

            def _replay(self, db_session, data):
                if not self.isAuthed:
                    return False
                return manager_ext.bot.songrequest_manager.replay_function()

            def _requeue(self, db_session, data):
                if not self.isAuthed or "database_id" not in data or not isint(data["database_id"]):
                    return False
                return manager_ext.bot.songrequest_manager.requeue_function(int(data["database_id"]), self.login)

            def _move(self, db_session, data):
                if (
                    not self.isAuthed
                    or "database_id" not in data
                    or "to_id" not in data
                    or not isint(data["to_id"])
                    or not isint(data["database_id"])
                ):
                    return False
                return manager_ext.bot.songrequest_manager.move_function(int(data["database_id"]), int(data["to_id"]))

            def _remove(self, db_session, data):
                if not self.isAuthed or "database_id" not in data or not isint(data["database_id"]):
                    return False
                return manager_ext.bot.songrequest_manager.remove_function(int(data["database_id"]))

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

        reactor_thread = threading.Thread(
            target=reactor_run,
            args=(reactor, factory, port, None, unix_socket_path),
            name="SongRequestWebSocketServerThread",
        )
        reactor_thread.daemon = True
        reactor_thread.start()


class SongRequestWebSocketManager:
    def __init__(self, bot):
        self.clients = []
        self.server = None
        self.bot = bot
        cfg = bot.config["songrequest-websocket"]
        try:
            if cfg["enabled"] == "1":
                try:
                    from twisted.python import log as twisted_log

                    twisted_log.addObserver(SongRequestWebSocketManager.on_log_message)
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
                if ssl and (key_path == "" or crt_path == ""):
                    log.error("SSL enabled in config, but missing key_path or crt_path")
                    return
                self.server = SongRequestWebSocketServer(self, port, ssl, key_path, crt_path, unix_socket_path)
        except:
            log.exception("Uncaught exception in SongRequestWebSocketManager")

    def emit(self, event, data={}):
        if self.server:
            payload = json.dumps({"event": event, "data": data}).encode("utf8")
            for client in self.server.clients:
                if client.isAuthed:
                    client.sendMessage(payload, False)

    @staticmethod
    def on_log_message(message, isError=False, printed=False):
        if isError:
            log.error(message["message"])
        else:
            pass

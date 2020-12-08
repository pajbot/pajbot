import json
import logging
import threading
from pathlib import Path

from twisted.internet import reactor
from autobahn.twisted.websocket import WebSocketServerFactory, WebSocketServerProtocol

from pajbot.models.songrequest import SongrequestQueue, SongrequestHistory, SongRequestSongInfo
from pajbot.managers.songrequest import find_youtube_id_in_string, find_youtube_video_by_search, find_backup_playlist_id
from pajbot.managers.db import DBManager
from pajbot.exc import (
    ManagerDisabled,
    InvalidState,
    InvalidVolume,
    InvalidSong,
    UserNotFound,
    InvalidPlaylist,
    SongBanned,
)

import pajbot.utils as utils

log = logging.getLogger("pajbot")


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
                self.login = None
                WebSocketServerProtocol.__init__(self)

            def onOpen(self):
                SongRequestWebSocketServer.clients.append(self)

            def onMessage(self, payload, isBinary):
                with DBManager.create_session_scope() as db_session:
                    if not isBinary:
                        try:
                            json_msg = json.loads(payload)
                        except:
                            self._close_conn()
                            return
                        if "event" not in json_msg:
                            self._close_conn()
                            return
                        switcher = {
                            "AUTH": self._auth,
                            "PAUSE": self._pause,
                            "RESUME": self._resume,
                            "NEXT": self._next,
                            "PREVIOUS": self._previous,
                            "SEEK": self._seek,
                            "VOLUME": self._volume,
                            "SHOW_VIDEO": self._show_video,
                            "HIDE_VIDEO": self._hide_video,
                            "REQUEST_STATE": self._request_state,
                            "AUTO_PLAY_STATE": self._auto_play_state,
                            "BACKUP_PLAYLIST_STATE": self._backup_playlist_state,
                            "USE_SPOTIFY_STATE": self._use_spotify_state,
                            "PLAY_ON_STREAM_STATE": self._play_on_stream_state,
                            "MOVE": self._move,
                            "FAVOURITE": self._favourite,
                            "UNFAVOURITE": self._unfavourite,
                            "BAN": self._ban,
                            "UNBAN": self._unban,
                            "DELETE": self._delete,
                            "REQUEST": self._request,
                            "ADD_MEDIA": self._add_media,
                            "SET_BACKUP_PLAYLIST": self._set_backup_playlist,
                            "READY": self._ready,
                        }
                        method = switcher.get(json_msg["event"].upper(), None)
                        try:
                            if not manager_ext.bot.songrequest_manager.states["enabled"]:
                                self._close_conn()
                                return
                        except AttributeError:
                            self._close_conn()
                            return

                        if not method:
                            self._close_conn()
                            return

                        resp, alert = method(db_session, json_msg.get("data", None))
                        if alert:
                            self.sendMessage(
                                json.dumps({"event": "alert_message", "data": alert}).encode("utf8"), False
                            )

                        if resp == 0:
                            self._close_conn()

            def onClose(self, wasClean, code, reason):
                SongRequestWebSocketServer.clients.remove(self)

            def _close_conn(self):
                self.sendClose()

            def _pause(self, db_session, data):
                if not self.isAuthed:
                    return 0, None

                try:
                    manager_ext.bot.songrequest_manager.pause_function()
                except (ManagerDisabled, InvalidState):
                    return 0, None

                return 1, None

            def _resume(self, db_session, data):
                if not self.isAuthed:
                    return 0, None

                try:
                    manager_ext.bot.songrequest_manager.resume_function()
                except (ManagerDisabled, InvalidState):
                    return 0, None

                return 1, None

            def _ready(self, db_session, data):
                if not self.isAuthed:
                    return 0, None

                try:
                    manager_ext.bot.songrequest_manager.ready_function()
                except (ManagerDisabled, InvalidState):
                    return 0, None

                return 1, None

            def _show_video(self, db_session, data):
                if not self.isAuthed:
                    return 0, None

                try:
                    manager_ext.bot.songrequest_manager.show_function()
                except (ManagerDisabled, InvalidState):
                    return 0, None

                return 1, {"success": True, "header": "Video Shown", "text": "", "duration": 2000}

            def _hide_video(self, db_session, data):
                if not self.isAuthed:
                    return 0, None

                try:
                    manager_ext.bot.songrequest_manager.hide_function()
                except (ManagerDisabled, InvalidState):
                    return 0, None

                return 1, {"success": True, "header": "Video Hidden", "text": "", "duration": 2000}

            def _request_state(self, db_session, data):
                if not self.isAuthed or "value" not in data:
                    return 0, None

                try:
                    manager_ext.bot.songrequest_manager.request_state_function(data["value"])
                except (ManagerDisabled, InvalidState):
                    return 0, None

                return (
                    1,
                    {
                        "success": True,
                        "header": f"Requests have been {'enabled' if data['value'] else 'disabled'}",
                        "text": "",
                        "duration": 2000,
                    },
                )

            def _auto_play_state(self, db_session, data):
                if not self.isAuthed or "value" not in data:
                    return 0, None

                try:
                    manager_ext.bot.songrequest_manager.auto_play_state_function(data["value"])
                except (ManagerDisabled, InvalidState):
                    return 0, None

                return (
                    1,
                    {
                        "success": True,
                        "header": f"Auto play has been {'enabled' if data['value'] else 'disabled'}",
                        "text": "",
                        "duration": 2000,
                    },
                )

            def _backup_playlist_state(self, db_session, data):
                if not self.isAuthed or "value" not in data:
                    return 0, None

                try:
                    manager_ext.bot.songrequest_manager.backup_playlist_state_function(data["value"])
                except (ManagerDisabled, InvalidState):
                    return 0, None

                return (
                    1,
                    {
                        "success": True,
                        "header": f"Backup playlist has been {'enabled' if data['value'] else 'disabled'}",
                        "text": "",
                        "duration": 2000,
                    },
                )

            def _use_spotify_state(self, db_session, data):
                if not self.isAuthed or "value" not in data:
                    return 0, None

                try:
                    manager_ext.bot.songrequest_manager.use_spotify_state_function(data["value"])
                except (ManagerDisabled, InvalidState):
                    return 0, None

                return (
                    1,
                    {
                        "success": True,
                        "header": f"Spotify has been {'enabled' if data['value'] else 'disabled'}",
                        "text": "",
                        "duration": 2000,
                    },
                )

            def _play_on_stream_state(self, db_session, data):
                if not self.isAuthed or "value" not in data:
                    return 0, None

                try:
                    manager_ext.bot.songrequest_manager.play_on_stream_function(data["value"])
                except (ManagerDisabled, InvalidState):
                    return 0, None

                return (
                    1,
                    {
                        "success": True,
                        "header": "Audio will be played in the browser"
                        if data["value"]
                        else "Audio will be played on the stream",
                        "text": "",
                        "duration": 2000,
                    },
                )

            def _next(self, db_session, data):
                if not self.isAuthed:
                    return 0, None

                try:
                    manager_ext.bot.songrequest_manager.skip_function(self.login)
                except (ManagerDisabled, UserNotFound):
                    return 0, None

                return 1, {"success": True, "header": "Song has been skipped", "text": "", "duration": 2000}

            def _previous(self, db_session, data):
                if not self.isAuthed:
                    return 0, None

                try:
                    manager_ext.bot.songrequest_manager.previous_function(self.login)
                except (ManagerDisabled, UserNotFound):
                    return 0, None

                return 1, None

            def _seek(self, db_session, data):
                if not self.isAuthed or "seek_time" not in data is False:
                    return 0, None

                try:
                    manager_ext.bot.songrequest_manager.seek_function(data["seek_time"])
                except (ManagerDisabled, InvalidSong):
                    return 0, None

                return 1, None

            def _volume(self, db_session, data):
                if not self.isAuthed or not data or "volume" not in data:
                    return 0, None

                try:
                    manager_ext.bot.songrequest_manager.volume_function(int(data["volume"]))
                except (ManagerDisabled, InvalidVolume):
                    return 0, None

                return 1, None

            def _move(self, db_session, data):
                if not self.isAuthed or not data or "database_id" not in data or "to_id" not in data:
                    return 0, None

                try:
                    manager_ext.bot.songrequest_manager.move_function(int(data["database_id"]), int(data["to_id"]) - 1)
                except (ManagerDisabled, InvalidSong):
                    return 0, None

                return 1, None

            def _favourite(self, db_session, data):
                if (
                    not self.isAuthed
                    or not data
                    or (
                        "database_id" not in data
                        and "songinfo_database_id" not in data
                        and "hist_database_id" not in data
                    )
                ):
                    return 0, None

                try:
                    manager_ext.bot.songrequest_manager.favourite_function(
                        database_id=data.get("database_id", None),
                        hist_database_id=data.get("hist_database_id", None),
                        songinfo_database_id=data.get("songinfo_database_id", None),
                    )
                except (ManagerDisabled, InvalidSong):
                    return 0, None

                return 1, {"success": True, "header": "Added to the favourites", "text": "", "duration": 2000}

            def _unfavourite(self, db_session, data):
                if (
                    not self.isAuthed
                    or not data
                    or (
                        "database_id" not in data
                        and "songinfo_database_id" not in data
                        and "hist_database_id" not in data
                    )
                ):
                    return 0, None

                try:
                    manager_ext.bot.songrequest_manager.unfavourite_function(
                        database_id=data.get("database_id", None),
                        hist_database_id=data.get("hist_database_id", None),
                        songinfo_database_id=data.get("songinfo_database_id", None),
                    )
                except (ManagerDisabled, InvalidSong):
                    return 0, None

                return 1, {"success": True, "header": "Removed from the favourites", "text": "", "duration": 2000}

            def _request(self, db_session, data):
                if (
                    not self.isAuthed
                    or not data
                    or (
                        "database_id" not in data
                        and "songinfo_database_id" not in data
                        and "hist_database_id" not in data
                        and "video_id" not in data
                    )
                ):
                    return 0, None

                try:
                    manager_ext.bot.songrequest_manager.request_function(
                        requested_by=self.login,
                        video_id=data.get("video_id", None),
                        database_id=data.get("database_id", None),
                        hist_database_id=data.get("hist_database_id", None),
                        songinfo_database_id=data.get("songinfo_database_id", None),
                    )
                except SongBanned:
                    return (
                        1,
                        {"success": False, "header": "That song is currently banned", "text": "", "duration": 2000},
                    )

                except (ManagerDisabled, UserNotFound, InvalidSong):
                    return 0, None

                return 1, {"success": True, "header": "Song added to queue", "text": "", "duration": 2000}

            def _ban(self, db_session, data):
                if (
                    not self.isAuthed
                    or not data
                    or (
                        "database_id" not in data
                        and "songinfo_database_id" not in data
                        and "hist_database_id" not in data
                    )
                ):
                    return 0, None

                try:
                    manager_ext.bot.songrequest_manager.ban_function(
                        database_id=data.get("database_id", None),
                        hist_database_id=data.get("hist_database_id", None),
                        songinfo_database_id=data.get("songinfo_database_id", None),
                    )
                except (ManagerDisabled, InvalidSong):
                    return 0, None

                return 1, {"success": True, "header": "Song has been banned", "text": "", "duration": 2000}

            def _unban(self, db_session, data):
                if (
                    not self.isAuthed
                    or not data
                    or (
                        "database_id" not in data
                        and "songinfo_database_id" not in data
                        and "hist_database_id" not in data
                    )
                ):
                    return 0, None
                try:
                    manager_ext.bot.songrequest_manager.unban_function(
                        database_id=data.get("database_id", None),
                        hist_database_id=data.get("hist_database_id", None),
                        songinfo_database_id=data.get("songinfo_database_id", None),
                    )
                except (ManagerDisabled, InvalidSong):
                    return 0, None

                return 1, {"success": True, "header": "Song has been unbanned", "text": "", "duration": 2000}

            def _delete(self, db_session, data):
                if not self.isAuthed or not data or "database_id" not in data:
                    return 0, None

                try:
                    manager_ext.bot.songrequest_manager.remove_function(int(data["database_id"]))
                except (ManagerDisabled, InvalidSong):
                    return 0, None

                return (
                    1,
                    {"success": True, "header": "Song has been removed from the queue", "text": "", "duration": 2000},
                )

            def _add_media(self, db_session, data):
                if not self.isAuthed or not data or "search" not in data:
                    return 0, None

                youtube_id = find_youtube_id_in_string(data["search"])

                if youtube_id is False:
                    youtube_id = find_youtube_video_by_search(data["search"])
                    if youtube_id is None:
                        return (
                            1,
                            {
                                "success": False,
                                "header": "Could not find your song",
                                "text": data["search"],
                                "duration": 4000,
                            },
                        )

                try:
                    manager_ext.bot.songrequest_manager.request_function(requested_by=self.login, video_id=youtube_id)
                except SongBanned:
                    return (
                        1,
                        {"success": False, "header": "That song is currently banned", "text": "", "duration": 2000},
                    )

                except (ManagerDisabled, UserNotFound, InvalidSong):
                    return 0, None

                return 1, {"success": True, "header": "Song has been added to the queue", "text": "", "duration": 2000}

            def _set_backup_playlist(self, db_session, data):
                if not self.isAuthed or not data or "backup_playlist" not in data:
                    return 0, None

                playlist_id = find_backup_playlist_id(data["backup_playlist"])
                if not playlist_id:
                    playlist_id = data["backup_playlist"]

                try:
                    manager_ext.bot.songrequest_manager.set_backup_playlist(playlist_id)
                except InvalidPlaylist:
                    return (
                        1,
                        {"success": False, "header": "Invalid Backup Playlist", "text": playlist_id, "duration": 4000},
                    )

                return (
                    1,
                    {
                        "success": True,
                        "header": "Backup Playlist set to " if playlist_id else "Backup playlist has been removed",
                        "text": f"https://www.youtube.com/playlist?list={playlist_id}" if playlist_id else "",
                        "duration": 4000,
                    },
                )

            def _auth(self, db_session, data):
                access_token = data["access_token"]
                user = manager_ext.bot.twitch_v5_api.user_from_access_token(
                    access_token, manager_ext.bot.twitch_helix_api, db_session
                )
                if not user or user.level < 500:
                    return 0, None

                self.isAuthed = True
                self.login = user.login
                self._dump_state(db_session)
                return 1, None

            def _dump_state(self, db_session):
                current_song = manager_ext.bot.songrequest_manager.current_song
                data = {
                    "volume": manager_ext.bot.songrequest_manager.volume,
                    "current_song": current_song.webjsonify() if current_song else {},
                    "module_state": manager_ext.bot.songrequest_manager.states,
                    "playlist": SongrequestQueue.get_playlist(db_session, limit=30),
                    "backup_playlist": SongrequestQueue.get_backup_playlist(db_session, limit=30),
                    "history_list": SongrequestHistory.get_history(db_session, limit=30),
                    "banned_list": [x.jsonify() for x in SongRequestSongInfo.get_banned(db_session)],
                    "favourite_list": [x.jsonify() for x in SongRequestSongInfo.get_favourite(db_session)],
                    "current_timestamp": str(utils.now().timestamp()),
                }
                payload = {"event": "initialize", "data": data}
                self.sendMessage(json.dumps(payload).encode("utf8"), False)

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

import websocket
import json
import threading
import time
import logging

from pajbot.managers.handler import HandlerManager
from pajbot.managers.schedule import ScheduleManager
from pajbot.managers.db import DBManager
from pajbot.models.user import User

log = logging.getLogger(__name__)


class PubSubAPI:
    def __init__(self, bot, token):
        self.bot = bot
        self.token = token
        self.schedule = None
        self.sent_ping = False
        try:
            self.receiveEventsThread._stop
        except:
            pass

        self.ws = websocket.WebSocketApp(
            "wss://pubsub-edge.twitch.tv",
            on_message=lambda ws, msg: self.on_message(ws, msg),
            on_error=lambda ws, msg: self.on_error(ws, msg),
            on_close=lambda ws: self.on_close(ws),
            on_open=lambda ws: self.on_open(ws),
        )

        self.receiveEventsThread = threading.Thread(target=self._receiveEventsThread)
        self.receiveEventsThread.daemon = True
        self.receiveEventsThread.start()

    def _receiveEventsThread(self):
        self.ws.run_forever()

    def on_message(self, ws, message):
        msg = json.loads(message)
        if msg["type"].lower() == "pong":
            self.sent_ping = False
        elif msg["type"].lower() == "reconnect":
            ScheduleManager.execute_now(self.reset)
        elif msg["type"].lower() == "message":
            if msg["data"]["topic"] == "channel-bits-events-v2." + self.bot.streamer_user_id:
                messageR = json.loads(msg["data"]["message"])
                user_id_of_cheer = str(messageR["data"]["user_id"])
                bits_cheered = str(messageR["data"]["bits_used"])
                with DBManager.create_session_scope() as db_session:
                    user = User.find_by_id(db_session, user_id_of_cheer)
                    if user is not None:
                        HandlerManager.trigger("on_cheer", True, user=user, bits_cheered=bits_cheered)

    def on_error(self, ws, error):
        log.error(f"pubsubapi : {error}")

    def on_close(self, ws):
        log.error("Socket disconnected. Donations no longer monitored")
        ScheduleManager.execute_delayed(10, self.reset)

    def on_open(self, ws):
        log.info("Pubsub Started!")
        self.sendData(
            {
                "type": "LISTEN",
                "data": {
                    "topics": ["channel-bits-events-v2." + self.bot.streamer_user_id],
                    "auth_token": self.token.token.access_token,
                },
            }
        )
        self.schedule = ScheduleManager.execute_every(120, self.check_connection)

    def check_connection(self):
        if not self.sent_ping:
            self.sendData({"type": "PING"})
            self.sent_ping = True
            ScheduleManager.execute_delayed(15, self.check_ping)

    def check_ping(self):
        if self.sent_ping:
            log.error("Pubsub connection timed out")
            ScheduleManager.execute_now(self.reset)

    def sendData(self, message):
        try:
            self.ws.send(json.dumps(message))
        except Exception as e:
            log.error(e)

    def reset(self):
        self.schedule.remove()
        self.__init__(self.bot, self.token)

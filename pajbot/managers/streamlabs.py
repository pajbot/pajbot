import logging
import threading
import socketio

from pajbot.managers.handler import HandlerManager
from pajbot.managers.db import DBManager
from pajbot.models.user import User

from currency_converter import CurrencyConverter


log = logging.getLogger(__name__)


class StreamLabsNameSpace(socketio.ClientNamespace):
    def on_connect(self):
        log.info("Connected to Streamlabs, Wait for Events")

    def on_event(self, data):
        if data["type"] == "donation":
            sub_data = data["message"][0]
            amount = float(str(sub_data["amount"]))
            username = str(sub_data["from"])
            currency = str(sub_data["currency"])
            c = CurrencyConverter()
            log.info(username)
            amount = round(c.convert(amount, currency, "USD"), 2)
            with DBManager.create_session_scope() as db_session:
                user = User.find_by_user_input(db_session, username)
                if user is not None:
                    log.info(f"User {user} donated ${amount}")
                    HandlerManager.trigger("on_donate", user=user, amount=amount)
        if "message" in data and "event" in data["message"]:
            if data["message"]["event"] == "play":
                if data["message"]["media"] is None:  # no new song
                    HandlerManager.trigger("resume_spotify")
                else:  # a new song
                    username = data["message"]["media"]["action_by"]
                    title = data["message"]["media"]["media_title"]
                    HandlerManager.trigger("pause_spotify", requestor=username, title=title)
            elif data["message"]["event"] == "updateControls":  # On play or pause on streamlabs
                HandlerManager.trigger("change_state", state=not data["message"]["controls"]["play"])

    def on_disconnect(self):
        log.error("Disconnected from steam elements")
        HandlerManager.trigger("streamlabs_reconnect")


class StreamLabsManager:
    def __init__(self, socket_access_token):
        self.socket_access_token = socket_access_token
        self.sio = socketio.Client()
        self.sio.register_namespace(StreamLabsNameSpace(""))

        HandlerManager.add_handler("streamlabs_reconnect", self.setupThread)

        self.mainThread = None
        self.setupThread()

    def setupThread(self):
        if self.mainThread is not None:
            self.mainThread.stop()
        self.mainThread = threading.Thread(target=self.connect)
        self.mainThread.daemon = True
        self.mainThread.start()

    def connect(self):
        self.sio.connect("https://sockets.streamlabs.com?token=" + self.socket_access_token)

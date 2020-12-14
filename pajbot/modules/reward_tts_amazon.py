import logging
import base64
import random
import re
import boto3
import botocore
import time
import threading

from pajbot.models.command import Command
from pajbot.models.user import User
from pajbot.managers.handler import HandlerManager
from pajbot.managers.db import DBManager
from pajbot.modules import BaseModule
from pajbot.modules import ModuleSetting

log = logging.getLogger(__name__)


neuralVoices = [
    "Amy",
    "Brian",
    "Camila",
    "Emma",
    "Ivy",
    "Joanna",
    "Joey",
    "Justin",
    "Kendra",
    "Kimberly",
    "Lupe",
    "Matthew",
    "Salli",
]
normalVoices = [
    "Aditi",
    "Astrid",
    "Bianca",
    "Carla",
    "Celine",
    "Chantal",
    "Conchita",
    "Cristiano",
    "Enrique",
    "Filiz",
    "Geraint",
    "Giorgio",
    "Hans",
    "Ines",
    "Jacek",
    "Lea",
    "Liv",
    "Lotte",
    "Lucia",
    "Mads",
    "Marlene",
    "Mathieu",
    "Maxim",
    "Mia",
    "Miguel",
    "Mizuki",
    "Naja",
    "Nicole",
    "Penelope",
    "Raveena",
    "Ricardo",
    "Ruben",
    "Russell",
    "Seoyeon",
    "Takumi",
    "Tatyana",
    "Vicki",
    "Vitoria",
    "Zeina",
    "Zhiyu",
]
allVoices = neuralVoices + normalVoices
voiceSearch = re.compile(r"^\w+:")

WIDGET_ID = 6


class RewardTTSModuleAmazon(BaseModule):
    ID = __name__.split(".")[-1]
    NAME = "Reward TTS - Amazon"
    DESCRIPTION = "Play text-to-speech based off highlighted messages or redeemed reward"
    CATEGORY = "Feature"
    SETTINGS = [
        ModuleSetting(
            key="tts_voice",
            label="Text-to-speech voice",
            type="options",
            required=True,
            default="Nicole",
            options=allVoices,
        ),
        ModuleSetting(key="random_voice", label="Use random voice", type="boolean", required=True, default=False),
        ModuleSetting(key="sub_only", label="Subscriber Only", type="boolean", required=True, default=False),
        ModuleSetting(
            key="redeemed_id",
            label="ID of redemeed prize",
            type="text",
            required=False,
            default="",
            constraints={"min_str_len": 36, "max_str_len": 36},
        ),
        ModuleSetting(
            key="sleep_delay",
            label="Duration to wait before playing tts to check if message was okay",
            type="number",
            required=False,
            default=5,
            constraints={"min_value": 0, "max_value": 10},
        ),
        ModuleSetting(key="disable_effects", label="Disable amazon polly effects", type="boolean", required=True, default=False),
    ]

    def command_skip(self, bot, **rest):
        bot.websocket_manager.emit(widget_id=WIDGET_ID, event="skip_highlight")

    def generateTTS(self, username, message):
        if self.bot.is_bad_message(message):
            return

        voiceResult = voiceSearch.search(message)
        if voiceResult is not None:
            ttsVoice = voiceResult.group()[:-1]
            if ttsVoice in allVoices:
                message = message[len(ttsVoice) + 1 :]
        else:
            ttsVoice = random.choice(allVoices) if self.settings["random_voice"] else self.settings["tts_voice"]

        synthArgs = {
            "Engine": "neural" if ttsVoice in neuralVoices else "standard",
            "OutputFormat": "mp3",
            "Text": f"<speak>{message}</speak>",
            "TextType": "ssml",
            "VoiceId": ttsVoice,
        }
        if self.settings["disable_effects"]:
            message = re.sub(r"<.*?>", "", message)

        try:
            synthResp = self.pollyClient.synthesize_speech(**synthArgs)
        except botocore.exceptions.ClientError as e:
            # Some limitation, eg "This voice does not support one of the used SSML features"
            log.exception(f"Error when trying to generate TTS: {e}")
            synthArgs["Text"] = message
            synthArgs["TextType"] = "text"
            synthResp = self.pollyClient.synthesize_speech(**synthArgs)
        except botocore.errorfactory.InvalidSsmlException:
            self.bot.whisper_login(username, "Your message syntax is malformed. Falling back to normal.")
            synthArgs["Text"] = message
            synthArgs["TextType"] = "text"
            synthResp = self.pollyClient.synthesize_speech(**synthArgs)

        payload = {
            "speech": base64.b64encode(synthResp["AudioStream"].read()).decode("utf-8"),
            "voice": ttsVoice,
            "user": username,
            "message": message,
        }
        self.bot.websocket_manager.emit(widget_id=WIDGET_ID, event="highlight", data=payload)

    def isHighlightedMessage(self, event):
        for eventTag in event.tags:
            if eventTag["value"] == "highlighted-message":
                return True

        return False

    def isReward(self, event):
        for eventTag in event.tags:
            if eventTag["key"] == "custom-reward-id":
                return eventTag["value"]

        return False

    def on_message(self, source, message, event, **rest):
        if (not self.settings["redeemed_id"] and not self.isHighlightedMessage(event)) or (self.settings["redeemed_id"] and self.isReward(event) != self.settings["redeemed_id"]) or (self.settings["sub_only"] and not source.subscriber):
            return

        thread = threading.Thread(target=self.threaded_delay, args=(source, message), daemon=True)
        thread.start()
        # self.generateTTS(source.name, message)

    def threaded_delay(self, source, message):
        time.sleep(self.settings["sleep_delay"])
        with DBManager.create_session_scope() as db_session:
            user = db_session.query(User).filter_by(id=source.id).one_or_none()
            if user.timed_out:
                return

        self.generateTTS(source.name, message)

    def load_commands(self, **options):
        self.commands["skiptts"] = Command.raw_command(
            self.command_skip, level=1000, description="Skip currently playing reward TTS"
        )

    def enable(self, bot):
        if not bot:
            return
        try:
            self.pollyClient = boto3.Session().client("polly")
        except:
            log.warning("RewardTTSModule is enabled without .aws in the config")
            return

        HandlerManager.add_handler("on_message", self.on_message)

    def disable(self, bot):
        if not bot:
            return

        HandlerManager.remove_handler("on_message", self.on_message)

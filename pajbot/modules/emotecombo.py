import logging

from pajbot.managers.handler import HandlerManager
from pajbot.modules import BaseModule

log = logging.getLogger(__name__)


class EmoteComboModule(BaseModule):
    ID = __name__.split(".")[-1]
    NAME = "Emote Combo (web interface)"
    DESCRIPTION = "Shows emote combos in the web interface CLR thing"
    CATEGORY = "Feature"
    SETTINGS = []  # TODO setting to configure equal emotes, e.g. monkaPickle and nymnPickle

    def __init__(self, bot):
        super().__init__(bot)
        self.emote_count = 0
        self.current_emote = None

    def inc_emote_count(self):
        self.emote_count += 1
        if self.emote_count >= 5:
            self.bot.websocket_manager.emit("emote_combo", {"emote": self.current_emote, "count": self.emote_count})

    def reset(self):
        self.emote_count = 0
        self.current_emote = None

    def on_message(self, emote_instances, emote_counts, whisper, **rest):
        if whisper:
            return True

        # Check if the message contains exactly one unique emote
        num_unique_emotes = len(emote_counts)
        if num_unique_emotes != 1:
            self.reset()
            return True

        new_emote = emote_instances[0]["emote"]
        new_emote_code = new_emote["code"]

        # if there is currently a combo...
        if self.current_emote is not None:
            # and this emote is not equal to the combo emote...
            if self.current_emote["code"] != new_emote_code:
                # The emote of this message is not the one we were previously counting, reset.
                # We do not stop.
                # We start counting this emote instead.
                self.reset()

        if self.current_emote is None:
            self.current_emote = new_emote

        self.inc_emote_count()
        return True

    def enable(self, bot):
        HandlerManager.add_handler("on_message", self.on_message)

    def disable(self, bot):
        HandlerManager.remove_handler("on_message", self.on_message)

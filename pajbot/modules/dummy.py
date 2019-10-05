import logging

from pajbot.models.command import Command
from pajbot.modules import BaseModule
from pajbot.modules import ModuleSetting

log = logging.getLogger(__name__)


class DummyModule(BaseModule):

    ID = __name__.split(".")[-1]
    NAME = "Dummy module"
    DESCRIPTION = "This does not actually do anything"
    CATEGORY = "Debugging"
    HIDDEN = True
    SETTINGS = [
        ModuleSetting(
            key="who",
            label="Who did it?",
            type="text",
            required=True,
            placeholder="asdasd",
            default="reddit",
            constraints={"min_str_len": 2, "max_str_len": 15},
        ),
        ModuleSetting(key="boolean_shit", label="boolean setting!", type="boolean", required=True, default=False),
        ModuleSetting(
            key="timeout_length",
            label="Timeout length",
            type="number",
            required=True,
            placeholder="Timeout length in seconds",
            default=60,
            constraints={"min_value": 1, "max_value": 3600},
        ),
        ModuleSetting(
            key="options_test",
            label="Options test",
            type="options",
            required=True,
            default="a",
            options=["a", "b", "c"],
        ),
    ]

    def dummy_command(self, **options):
        log.info("asd")
        log.info(options)
        bot = options.get("bot", None)
        if bot:
            bot.say(f"we did it {self.settings['who']}!")

    def load_commands(self, **options):
        self.commands["dummy"] = Command.raw_command(self.dummy_command)

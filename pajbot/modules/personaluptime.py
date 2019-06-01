import logging

from pajbot.models.command import Command
from pajbot.modules import BaseModule
from pajbot.utils import time_since

log = logging.getLogger(__name__)


class PersonalUptimeModule(BaseModule):

    ID = __name__.split(".")[-1]
    NAME = "Personal Uptime"
    DESCRIPTION = "People can use !myuptime to check how long they've been watching the current stream"
    CATEGORY = "Feature"
    SETTINGS = []

    @staticmethod
    def cmd_puptime(**options):
        bot = options["bot"]
        source = options["source"]

        viewer_data = bot.stream_manager.get_viewer_data()

        if viewer_data is False:
            bot.say("{}, the stream is offline.".format(source.username_raw))
            return

        minutes_watched = viewer_data.get(source.username, None)
        if minutes_watched is None:
            bot.say("{}, You haven't been registered watching the stream yet WutFace".format(source.username_raw))
        else:
            minutes_watched = int(minutes_watched) * 60
            log.info(minutes_watched)
            bot.say(
                "{}, You have been watching the stream for ~{}".format(
                    source.username_raw, time_since(minutes_watched, 0)
                )
            )

    def load_commands(self, **options):
        self.commands["myuptime"] = Command.raw_command(self.cmd_puptime, delay_all=3, delay_user=60)

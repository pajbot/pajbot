import collections
import logging

from pajbot.managers.redis import RedisManager
from pajbot.streamhelper import StreamHelper
from pajbot.web.utils import requires_level

from flask import render_template
from flask.typing import ResponseReturnValue

log = logging.getLogger(__name__)


def init(page) -> None:
    @page.route("/streamer")
    @requires_level(500)
    def admin_streamer(**options) -> ResponseReturnValue:
        redis = RedisManager.get()
        streamer = StreamHelper.get_streamer()
        keys = StreamHelper.social_keys
        streamer_info_keys = [f"{streamer}:{key}" for key in keys.keys()]
        log.info(streamer_info_keys)
        streamer_info_list = redis.hmget("streamer_info", streamer_info_keys)
        streamer_info = collections.OrderedDict()
        for key in keys:
            value = streamer_info_list.pop(0)
            streamer_info[key] = {"value": value, "title": keys[key]["title"], "format": keys[key]["format"]}
        return render_template("admin/streamer.html", streamer_info=streamer_info)

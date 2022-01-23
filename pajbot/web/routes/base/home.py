import collections
import logging

from pajbot.managers.redis import RedisManager
from pajbot.streamhelper import StreamHelper

from flask import render_template

log = logging.getLogger(__name__)


def init(app):
    @app.route("/")
    def home():
        custom_content = ""

        redis = RedisManager.get()
        streamer = StreamHelper.get_streamer()

        keys = ("online", "viewers", "game")
        stream_data_keys = [f"{streamer}:{key}" for key in keys]
        stream_data_list = redis.hmget("stream_data", stream_data_keys)
        stream_data = {keys[x]: stream_data_list[x] for x in range(0, len(keys))}

        keys = StreamHelper.social_keys
        streamer_info_keys = [f"{streamer}:{key}" for key in keys.keys()]
        log.info(streamer_info_keys)
        streamer_info_list = redis.hmget("streamer_info", streamer_info_keys)
        streamer_info = collections.OrderedDict()
        for key in keys:
            value = streamer_info_list.pop(0)
            if value:
                streamer_info[key] = {
                    "value": keys[key]["format"].format(value),
                    "title": keys[key]["title"],
                    "format": keys[key]["format"],
                }

        current_quest_key = f"{StreamHelper.get_streamer()}:current_quest"
        current_quest_id = redis.get(current_quest_key)
        if current_quest_id is not None:
            current_quest = app.module_manager[current_quest_id]
            if current_quest:
                current_quest.load_data()
        else:
            current_quest = None

        return render_template(
            "home.html",
            custom_content=custom_content,
            current_quest=current_quest,
            stream_data=stream_data,
            streamer_info=streamer_info,
        )

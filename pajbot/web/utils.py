from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, List, Set

import datetime
import json
import logging
from functools import update_wrapper, wraps

import pajbot.exc
import pajbot.managers
from pajbot import utils
from pajbot.apiwrappers.base import BaseAPI
from pajbot.apiwrappers.twitch.badges import BadgeNotFoundError
from pajbot.managers.db import DBManager
from pajbot.managers.redis import RedisManager
from pajbot.models.module import ModuleManager
from pajbot.models.user import User
from pajbot.streamhelper import StreamHelper
from pajbot.utils import time_method

from flask import abort, make_response, session

if TYPE_CHECKING:
    from pajbot.apiwrappers.twitch.badges import TwitchBadgesAPI
    from pajbot.apiwrappers.twitch.helix import TwitchHelixAPI
    from pajbot.models.user import UserBasics

log = logging.getLogger(__name__)


def requires_level(level):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if "user" not in session:
                abort(403)
            with DBManager.create_session_scope() as db_session:
                user = db_session.query(User).filter_by(id=session["user"]["id"]).one_or_none()
                if user is None:
                    abort(403)

                if user.level < level:
                    abort(403)

                db_session.expunge(user)
                kwargs["user"] = user

            return f(*args, **kwargs)

        return update_wrapper(decorated_function, f)

    return decorator


def nocache(view):
    @wraps(view)
    def no_cache(*args, **kwargs):
        response = make_response(view(*args, **kwargs))
        response.headers["Last-Modified"] = utils.now()
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "-1"
        return response

    return update_wrapper(no_cache, view)


def download_logo(twitch_helix_api: TwitchHelixAPI, streamer: UserBasics) -> None:
    logo_url = twitch_helix_api.get_profile_image_url(streamer.id)

    if logo_url is None:
        log.warn(f"Failed to query Twitch API for the profile image url of streamer {streamer.login}")
        return

    logo_raw_path = f"static/images/logo_{streamer.login}.png"

    # returns bytes
    logo_image_bytes = BaseAPI(None).get_binary(logo_url)

    # write full-size image...
    with open(logo_raw_path, "wb") as logo_raw_file:
        logo_raw_file.write(logo_image_bytes)


def download_sub_badge(twitch_badges_api: TwitchBadgesAPI, streamer: UserBasics, subscriber_badge_version: str) -> None:
    try:
        subscriber_badge = twitch_badges_api.get_channel_subscriber_badge(streamer.id, subscriber_badge_version)
    except BadgeNotFoundError as e:
        log.warn(f"Unable to download subscriber badge: {e}")
        return

    subscriber_badge_path = f"static/images/badge_sub_{streamer.login}.png"

    # returns bytes
    subscriber_badge_bytes = BaseAPI(None).get_binary(subscriber_badge.image_url_1x)

    # write image...
    with open(subscriber_badge_path, "wb") as subscriber_badge_file:
        subscriber_badge_file.write(subscriber_badge_bytes)


@time_method
def get_cached_commands() -> List[Dict[str, Any]]:
    CACHE_TIME = 30  # seconds

    redis = RedisManager.get()
    commands_key = f"{StreamHelper.get_streamer()}:cache:commands"
    commands = redis.get(commands_key)
    if commands is not None:
        cached_bot_command_list = json.loads(commands)
        if not isinstance(cached_bot_command_list, list):
            return []
        return cached_bot_command_list

    log.debug("Updating commands...")
    bot_commands = pajbot.managers.command.CommandManager(
        socket_manager=None, module_manager=ModuleManager(None).load(), bot=None
    ).load(load_examples=True)
    bot_commands_list = bot_commands.parse_for_web()

    bot_commands_list.sort(key=lambda x: (x.id or -1, x.main_alias))
    jsonified_bot_commands_list = [c.jsonify() for c in bot_commands_list]
    redis.setex(commands_key, value=json.dumps(jsonified_bot_commands_list, separators=(",", ":")), time=CACHE_TIME)

    return jsonified_bot_commands_list


@time_method
def get_cached_enabled_modules() -> Set[str]:
    CACHE_TIME = 30  # seconds
    CACHE_KEY = f"{StreamHelper.get_streamer()}:cache:enabled_modules"

    enabled_modules: Set[str] = set()

    redis = RedisManager.get()
    redis_enabled_modules = redis.get(CACHE_KEY)
    if redis_enabled_modules is not None:
        cached_enabled_modules = json.loads(redis_enabled_modules)
        if not isinstance(cached_enabled_modules, list):
            log.warning("Poorly cached module states")
            return enabled_modules
        return set(cached_enabled_modules)

    log.debug("Updating enabled modules...")
    module_manager = ModuleManager(None).load()
    for module in module_manager.modules:
        enabled_modules.add(module.ID)
    redis.setex(CACHE_KEY, value=json.dumps(list(enabled_modules)), time=CACHE_TIME)

    return enabled_modules


def json_serial(obj):
    if isinstance(obj, datetime.datetime):
        serial = obj.isoformat()
        return serial
    try:
        return obj.jsonify()
    except:
        log.exception("Unable to serialize object with `jsonify`")
        raise


def jsonify_query(query):
    return [v.jsonify() for v in query]


def seconds_to_vodtime(t):
    s = int(t)
    h = s / 3600
    m = s % 3600 / 60
    s = s % 60
    return "%dh%02dm%02ds" % (h, m, s)


def format_tb(tb, limit=None):
    import traceback

    stacktrace = traceback.extract_tb(tb)

    ret = ""
    for stack in stacktrace:
        ret += f"*{stack[0]}*:{stack[1]} ({stack[2]}): {stack[3]}\n"

    return ret

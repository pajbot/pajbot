from __future__ import annotations

from typing import TYPE_CHECKING, Any

import datetime
import json
import logging
from functools import update_wrapper, wraps

import pajbot.exc
import pajbot.managers
from pajbot import utils
from pajbot.apiwrappers.base import BaseAPI
from pajbot.managers.db import DBManager
from pajbot.managers.redis import RedisManager
from pajbot.models.module import ModuleManager
from pajbot.models.user import User
from pajbot.streamhelper import StreamHelper
from pajbot.utils import time_method

from flask import abort, make_response, session

if TYPE_CHECKING:
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


def download_sub_badge(twitch_helix_api: TwitchHelixAPI, streamer: UserBasics, subscriber_badge_version: str) -> None:
    out_path = f"static/images/badge_sub_{streamer.login}.png"

    log.info(f"Downloading sub badge for {streamer.login} (badge version {subscriber_badge_version}) to {out_path}")

    badge_sets = twitch_helix_api.get_channel_badges(streamer.id)

    try:
        subscriber_badge_set = next(badge_set for badge_set in badge_sets if badge_set.set_id == "subscriber")
    except StopIteration:
        log.error(f"No subscriber badge set found for {streamer.login}")
        return

    try:
        subscriber_badge = next(
            badge_version
            for badge_version in subscriber_badge_set.versions
            if badge_version.id == subscriber_badge_version
        )
    except StopIteration:
        log.error(
            f"No subscriber badge found for {streamer.login} with the requested version {subscriber_badge_version}"
        )
        return

    # returns bytes
    subscriber_badge_bytes = BaseAPI(None).get_binary(subscriber_badge.image_url_1x)

    # write image...
    with open(out_path, "wb") as subscriber_badge_file:
        subscriber_badge_file.write(subscriber_badge_bytes)


def get_top_emotes() -> list[dict[str, str]]:
    redis = RedisManager.get()
    streamer = StreamHelper.get_streamer()

    top_emotes_list: list[dict[str, str]] = []
    top_emotes = {  # noqa: C416
        emote: emote_count
        for emote, emote_count in sorted(
            redis.zscan_iter(f"{streamer}:emotes:count"), key=lambda e_ecount_pair: e_ecount_pair[1], reverse=True
        )[:100]
    }

    if top_emotes:
        top_emotes_list.extend(
            {"emote_name": emote, "emote_count": str(int(emote_count))} for emote, emote_count in top_emotes.items()
        )

    return top_emotes_list


@time_method
def get_cached_commands() -> list[dict[str, Any]]:
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
def get_cached_enabled_modules() -> set[str]:
    CACHE_TIME = 30  # seconds
    CACHE_KEY = f"{StreamHelper.get_streamer()}:cache:enabled_modules"

    enabled_modules: set[str] = set()

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

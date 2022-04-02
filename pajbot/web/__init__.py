import logging
import os

import pajbot.config as cfg
from pajbot.apiwrappers.authentication.client_credentials import ClientCredentials
from pajbot.apiwrappers.authentication.token_manager import AppAccessTokenManager
from pajbot.apiwrappers.twitch.badges import TwitchBadgesAPI
from pajbot.apiwrappers.twitch.helix import TwitchHelixAPI
from pajbot.apiwrappers.twitch.id import TwitchIDAPI
from pajbot.constants import VERSION
from pajbot.utils import extend_version_if_possible

from flask import Flask
from flask_wtf.csrf import CSRFProtect

# 30 days
SECRET_KEY_EXPIRY_SECONDS = 86400 * 30

app = Flask(
    __name__,
    static_folder=os.path.join(os.path.dirname(os.path.abspath(__file__ + "/../..")), "static"),
    template_folder=os.path.join(os.path.dirname(os.path.abspath(__file__ + "/../..")), "templates"),
)

app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

csrf = CSRFProtect(app)

app.url_map.strict_slashes = False

log = logging.getLogger(__name__)


def _load_secret_key(bot_id: str, streamer_id: str) -> str:
    from secrets import token_urlsafe

    from pajbot.managers.redis import RedisManager

    redis = RedisManager.get()

    key = f"web_secret_key:{bot_id}:{streamer_id}"

    value = redis.get(key)

    if value is None:
        value = token_urlsafe(64)
        redis.set(key, value, ex=SECRET_KEY_EXPIRY_SECONDS)

    return value


def init(args):
    import subprocess
    import sys

    import pajbot.utils
    import pajbot.web.common
    import pajbot.web.routes
    from pajbot.managers.db import DBManager
    from pajbot.managers.redis import RedisManager
    from pajbot.models.module import ModuleManager
    from pajbot.models.sock import SocketClientManager
    from pajbot.streamhelper import StreamHelper
    from pajbot.utils import load_config
    from pajbot.web.models import errors
    from pajbot.web.utils import download_logo, download_sub_badge

    from flask import request, session

    config = load_config(args.config)

    api_client_credentials = ClientCredentials(
        config["twitchapi"]["client_id"],
        config["twitchapi"]["client_secret"],
        config["twitchapi"].get("redirect_uri", f"https://{config['web']['domain']}/login/authorized"),
    )

    redis_options = {}
    if "redis" in config:
        redis_options = dict(config["redis"])

    RedisManager.init(redis_options)

    twitch_id_api = TwitchIDAPI(api_client_credentials)
    app_token_manager = AppAccessTokenManager(twitch_id_api, RedisManager.get())
    twitch_helix_api = TwitchHelixAPI(RedisManager.get(), app_token_manager)
    twitch_badges_api = TwitchBadgesAPI(RedisManager.get())

    app.api_client_credentials = api_client_credentials
    app.twitch_id_api = twitch_id_api
    app.twitch_helix_api = twitch_helix_api

    if "web" not in config:
        log.error("Missing [web] section in config.ini")
        sys.exit(1)

    app.streamer = cfg.load_streamer(config, twitch_helix_api)

    app.streamer_display = app.streamer.name
    if "streamer_name" in config["web"]:
        app.streamer_display = config["web"]["streamer_name"]

    app.bot_user = cfg.load_bot(config, twitch_helix_api)

    StreamHelper.init_streamer(app.streamer.login, app.streamer.id, app.streamer.name)

    try:
        download_logo(twitch_helix_api, app.streamer)
    except:
        log.exception("Error downloading the streamers profile picture")

    subscriber_badge_version = config["web"].get("subscriber_badge_version", "0")

    # Specifying a value of -1 in the config will disable sub badge downloading. Useful if you want to keep a custom version of a sub badge for a streamer
    if subscriber_badge_version != "-1":
        try:
            download_sub_badge(twitch_badges_api, app.streamer, subscriber_badge_version)
        except:
            log.exception("Error downloading the streamers subscriber badge")

    SocketClientManager.init(app.streamer.login)

    if config["web"].get("modules") is not None:
        log.warning(
            "DEPRECATED - [web] modules config is deprecated. Disabling options in the menu should now be done by disabling the module entirely from the Admin modules section."
        )

    app.bot_commands_list = []
    app.bot_config = config

    # https://flask.palletsprojects.com/en/1.1.x/quickstart/#sessions
    # https://flask.palletsprojects.com/en/1.1.x/api/#sessions
    # https://flask.palletsprojects.com/en/1.1.x/api/#flask.Flask.secret_key
    app.secret_key = _load_secret_key(app.bot_user.id, app.streamer.id)
    app.bot_dev = "flags" in config and "dev" in config["flags"] and config["flags"]["dev"] == "1"

    DBManager.init(config["main"]["db"])

    app.module_manager = ModuleManager(None).load()

    pajbot.web.routes.admin.init(app)
    pajbot.web.routes.api.init(app)
    pajbot.web.routes.base.init(app)

    # Make a CSRF exemption for the /api/v1/banphrases/test endpoint
    csrf.exempt("pajbot.web.routes.api.banphrases.apibanphrasetest")

    pajbot.web.common.filters.init(app)
    pajbot.web.common.assets.init(app)
    pajbot.web.common.menu.init(app)

    app.register_blueprint(pajbot.web.routes.clr.page)

    errors.init(app, config)
    pajbot.web.routes.clr.config = config

    version = VERSION
    last_commit = None

    if app.bot_dev:
        version = extend_version_if_possible(VERSION)

        try:
            last_commit = subprocess.check_output(["git", "log", "-1", "--format=%cd"]).decode("utf8").strip()
        except:
            log.exception("Failed to get last_commit, will not show last commit")

    default_variables = {
        "version": version,
        "last_commit": last_commit,
        "bot": {"name": app.bot_user.login},
        "site": {
            "domain": config["web"]["domain"],
            "deck_tab_images": cfg.get_boolean(config["web"], "deck_tab_images", False),
            "websocket": {"host": config["websocket"].get("host", f"wss://{config['web']['domain']}/clrsocket")},
        },
        "streamer": {"name": app.streamer_display, "full_name": app.streamer.login, "id": app.streamer.id},
        "request": request,
        "session": session,
        "google_analytics": config["web"].get("google_analytics", None),
    }

    @app.context_processor
    def current_time():
        current_time = {}
        current_time["current_time"] = pajbot.utils.now()
        return current_time

    @app.context_processor
    def inject_default_variables():
        return default_variables

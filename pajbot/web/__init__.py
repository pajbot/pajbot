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

app = Flask(
    __name__,
    static_folder=os.path.join(os.path.dirname(os.path.abspath(__file__ + "/../..")), "static"),
    template_folder=os.path.join(os.path.dirname(os.path.abspath(__file__ + "/../..")), "templates"),
)

app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

csrf = CSRFProtect(app)

app.url_map.strict_slashes = False

log = logging.getLogger(__name__)


def init(args):
    import subprocess
    import sys

    from flask import request
    from flask import session
    from flask_scrypt import generate_random_salt

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
    from pajbot.web.utils import download_logo
    from pajbot.web.utils import download_sub_badge

    config = load_config(args.config)

    api_client_credentials = ClientCredentials(
        config["twitchapi"]["client_id"], config["twitchapi"]["client_secret"], config["twitchapi"]["redirect_uri"]
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

    if "secret_key" not in config["web"]:
        salt = generate_random_salt()
        config.set("web", "secret_key", salt.decode("utf-8"))

        with open(args.config, "w") as configfile:
            config.write(configfile)

    streamer = config["main"]["streamer"]
    streamer_display = config["web"]["streamer_name"]
    streamer_user_id = twitch_helix_api.get_user_id(streamer)
    if streamer_user_id is None:
        raise ValueError("The streamer login name you entered under [main] does not exist on twitch.")
    StreamHelper.init_streamer(streamer, streamer_user_id, streamer_display)

    try:
        download_logo(twitch_helix_api, streamer, streamer_user_id)
    except:
        log.exception("Error downloading the streamers profile picture")

    subscriber_badge_version = config["web"].get("subscriber_badge_version", "0")

    # Specifying a value of -1 in the config will disable sub badge downloading. Useful if you want to keep a custom version of a sub badge for a streamer
    if subscriber_badge_version != "-1":
        try:
            download_sub_badge(twitch_badges_api, streamer, streamer_user_id, subscriber_badge_version)
        except:
            log.exception("Error downloading the streamers subscriber badge")

    SocketClientManager.init(streamer)

    app.bot_modules = config["web"].get("modules", "").split()
    app.bot_commands_list = []
    app.bot_config = config
    # https://flask.palletsprojects.com/en/1.1.x/quickstart/#sessions
    # https://flask.palletsprojects.com/en/1.1.x/api/#sessions
    # https://flask.palletsprojects.com/en/1.1.x/api/#flask.Flask.secret_key
    app.secret_key = config["web"]["secret_key"]
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
        "bot": {"name": config["main"]["nickname"]},
        "site": {
            "domain": config["web"]["domain"],
            "deck_tab_images": cfg.get_boolean(config["web"], "deck_tab_images", False),
            "websocket": {"host": config["websocket"].get("host", f"wss://{config['web']['domain']}/clrsocket")},
        },
        "streamer": {"name": streamer_display, "full_name": config["main"]["streamer"], "id": streamer_user_id},
        "modules": app.bot_modules,
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

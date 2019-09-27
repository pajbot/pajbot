import os

from flask import Flask

from pajbot.apiwrappers.authentication.client_credentials import ClientCredentials
from pajbot.apiwrappers.authentication.token_manager import AppAccessTokenManager
from pajbot.apiwrappers.twitch.helix import TwitchHelixAPI
from pajbot.apiwrappers.twitch.id import TwitchIDAPI
from pajbot.constants import VERSION
from pajbot.utils import extend_version_if_possible

app = Flask(
    __name__,
    static_folder=os.path.join(os.path.dirname(os.path.abspath(__file__ + "/../..")), "static"),
    template_folder=os.path.join(os.path.dirname(os.path.abspath(__file__ + "/../..")), "templates"),
)

app.url_map.strict_slashes = False


def init(args):
    import configparser
    import logging
    import subprocess
    import sys

    from flask import request
    from flask import session
    from flask_scrypt import generate_random_salt

    import pajbot.utils
    import pajbot.web.common
    import pajbot.web.routes
    from pajbot import constants
    from pajbot.managers.db import DBManager
    from pajbot.managers.redis import RedisManager
    from pajbot.managers.time import TimeManager
    from pajbot.models.module import ModuleManager
    from pajbot.models.sock import SocketClientManager
    from pajbot.streamhelper import StreamHelper
    from pajbot.utils import load_config
    from pajbot.web.models import errors
    from pajbot.web.utils import download_logo

    log = logging.getLogger(__name__)

    config = configparser.ConfigParser()

    config = load_config(args.config)
    config.read("webconfig.ini")

    api_client_credentials = ClientCredentials(
        config["twitchapi"]["client_id"], config["twitchapi"]["client_secret"], config["twitchapi"]["redirect_uri"]
    )

    redis_options = {}
    if "redis" in config:
        redis_options = dict(config["redis"])

    RedisManager.init(**redis_options)

    id_api = TwitchIDAPI(api_client_credentials)
    app_token_manager = AppAccessTokenManager(id_api, RedisManager.get())
    twitch_helix_api = TwitchHelixAPI(RedisManager.get(), app_token_manager)

    if "web" not in config:
        log.error("Missing [web] section in config.ini")
        sys.exit(1)

    if "pleblist_password_salt" not in config["web"]:
        salt = generate_random_salt()
        config.set("web", "pleblist_password_salt", salt.decode("utf-8"))

    if "pleblist_password" not in config["web"]:
        salt = generate_random_salt()
        config.set("web", "pleblist_password", salt.decode("utf-8"))

    if "secret_key" not in config["web"]:
        salt = generate_random_salt()
        config.set("web", "secret_key", salt.decode("utf-8"))

    if "logo" not in config["web"]:
        try:
            download_logo(twitch_helix_api, config["main"]["streamer"])
            config.set("web", "logo", "set")
        except:
            log.exception("Error downloading logo")

    StreamHelper.init_web(config["main"]["streamer"])
    SocketClientManager.init(config["main"]["streamer"])

    with open(args.config, "w") as configfile:
        config.write(configfile)

    app.bot_modules = config["web"].get("modules", "").split()
    app.bot_commands_list = []
    app.bot_config = config
    app.secret_key = config["web"]["secret_key"]

    DBManager.init(config["main"]["db"])
    TimeManager.init_timezone(config["main"].get("timezone", "UTC"))

    app.module_manager = ModuleManager(None).load()

    pajbot.web.routes.admin.init(app)
    pajbot.web.routes.api.init(app)
    pajbot.web.routes.base.init(app)

    pajbot.web.common.filters.init(app)
    pajbot.web.common.assets.init(app)
    pajbot.web.common.menu.init(app)

    app.register_blueprint(pajbot.web.routes.clr.page)

    errors.init(app, config)
    pajbot.web.routes.clr.config = config

    version = extend_version_if_possible(VERSION)

    try:
        last_commit = subprocess.check_output(["git", "log", "-1", "--format=%cd"]).decode("utf8").strip()
    except:
        log.exception("Failed to get last_commit, will not show last commit")
        last_commit = None

    default_variables = {
        "version": version,
        "last_commit": last_commit,
        "bot": {"name": config["main"]["nickname"]},
        "site": {
            "domain": config["web"]["domain"],
            "deck_tab_images": config.getboolean("web", "deck_tab_images"),
            "websocket": {
                "host": config["websocket"].get("host", "wss://{}/clrsocket".format(config["web"]["domain"]))
            },
        },
        "streamer": {"name": config["web"]["streamer_name"], "full_name": config["main"]["streamer"]},
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

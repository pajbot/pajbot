import json
import logging
import os

from flask import redirect
from flask import render_template
from flask import request
from flask import session
from flask import url_for
from flask_oauthlib.client import OAuth
from flask_oauthlib.client import OAuthException

from pajbot.managers.db import DBManager
from pajbot.managers.redis import RedisManager
from pajbot.models.user import User

log = logging.getLogger(__name__)


def init(app):
    oauth = OAuth(app)

    # enables the usage of 127.0.0.1:7221 over http for OAuth purposes.
    os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

    twitch = oauth.remote_app(
        "twitch",
        consumer_key=app.bot_config["webtwitchapi"]["client_id"],
        consumer_secret=app.bot_config["webtwitchapi"]["client_secret"],
        request_token_params={"scope": "user_read"},
        base_url="{}/kraken/".format(os.environ.get("APIPROXY_HOST", "http://127.0.0.1:7221")),
        request_token_url=None,
        access_token_method="POST",
        access_token_url="https://id.twitch.tv/oauth2/token",
        authorize_url="https://id.twitch.tv/oauth2/authorize",
    )

    @app.route("/login")
    def login():
        callback_url = (
            app.bot_config["webtwitchapi"]["redirect_uri"]
            if "redirect_uri" in app.bot_config["webtwitchapi"]
            else url_for("authorized", _external=True)
        )
        state = request.args.get("n") or request.referrer or None
        return twitch.authorize(callback=callback_url, state=state)

    @app.route("/bot_login")
    def bot_login():
        callback_url = (
            app.bot_config["webtwitchapi"]["redirect_uri"]
            if "redirect_uri" in app.bot_config["webtwitchapi"]
            else url_for("authorized", _external=True)
        )
        state = request.args.get("n") or request.referrer or None
        return twitch.authorize(
            callback=callback_url,
            state=state,
            scope="user_read user:edit user:read:email channel:moderate chat:edit chat:read whispers:read whispers:edit",
            force_verify="true",
        )

    @app.route("/login/error")
    def login_error():
        return render_template("login_error.html")

    @app.route("/login/authorized")
    def authorized():
        try:
            resp = twitch.authorized_response()
        except OAuthException:
            log.exception("An exception was caught while authorizing")
            next_url = get_next_url(request, "state")
            return redirect(next_url)
        except:
            log.exception("Unhandled exception while authorizing")
            return render_template("login_error.html")

        if resp is None:
            if "error" in request.args and "error_description" in request.args:
                log.warning(
                    "Access denied: reason={}, error={}".format(
                        request.args["error"], request.args["error_description"]
                    )
                )
            next_url = get_next_url(request, "state")
            return redirect(next_url)
        elif type(resp) is OAuthException:
            log.warning(resp.message)
            log.warning(resp.data)
            log.warning(resp.type)
            next_url = get_next_url(request, "state")
            return redirect(next_url)
        session["twitch_token"] = (resp["access_token"],)
        me = twitch.get("user")
        level = 100
        with DBManager.create_session_scope() as db_session:
            db_user = db_session.query(User).filter_by(username=me.data["name"].lower()).one_or_none()
            if db_user:
                level = db_user.level
        session["user"] = {"username": me.data["name"], "username_raw": me.data["display_name"], "level": level}

        if me.data["name"].lower() == app.bot_config["main"]["nickname"].lower():
            redis = RedisManager.get()
            redis.set("{}:token".format(app.bot_config["main"]["nickname"]), json.dumps(resp))

        next_url = get_next_url(request, "state")
        return redirect(next_url)

    def get_next_url(request, key="n"):
        next_url = request.args.get(key, "/")
        if next_url.startswith("//"):
            return "/"
        return next_url

    @app.route("/logout")
    def logout():
        session.pop("twitch_token", None)
        session.pop("user", None)
        next_url = get_next_url(request)
        if next_url.startswith("/admin"):
            next_url = "/"
        return redirect(next_url)

    @twitch.tokengetter
    def get_twitch_oauth_token():
        return session.get("twitch_token")

    def change_twitch_header(uri, headers, body):
        auth = headers.get("Authorization")
        if auth:
            auth = auth.replace("Bearer", "OAuth")
            headers["Authorization"] = auth
        return uri, headers, body

    twitch.pre_request = change_twitch_header

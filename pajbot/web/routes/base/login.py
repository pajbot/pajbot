import json
import logging

from flask import redirect
from flask import render_template
from flask import request
from flask import session
from flask import url_for
from flask_oauthlib.client import OAuth
from flask_oauthlib.client import OAuthException

from pajbot.apiwrappers.authentication.access_token import UserAccessToken
from pajbot.managers.db import DBManager
from pajbot.managers.redis import RedisManager
from pajbot.models.user import User, UserBasics

log = logging.getLogger(__name__)


def init(app):
    oauth = OAuth(app)

    twitch = oauth.remote_app(
        "twitch",
        consumer_key=app.bot_config["twitchapi"]["client_id"],
        consumer_secret=app.bot_config["twitchapi"]["client_secret"],
        request_token_params={"scope": "user_read"},
        base_url="https://api.twitch.tv/helix/",
        request_token_url=None,
        access_token_method="POST",
        access_token_url="https://id.twitch.tv/oauth2/token",
        authorize_url="https://id.twitch.tv/oauth2/authorize",
    )

    @app.route("/login")
    def login():
        callback_url = (
            app.bot_config["twitchapi"]["redirect_uri"]
            if "redirect_uri" in app.bot_config["twitchapi"]
            else url_for("authorized", _external=True)
        )
        state = request.args.get("n") or request.referrer or None
        return twitch.authorize(callback=callback_url, state=state)

    @app.route("/bot_login")
    def bot_login():
        callback_url = (
            app.bot_config["twitchapi"]["redirect_uri"]
            if "redirect_uri" in app.bot_config["twitchapi"]
            else url_for("authorized", _external=True)
        )
        state = request.args.get("n") or request.referrer or None
        return twitch.authorize(
            callback=callback_url,
            state=state,
            scope=(
                "user_read user:edit user:read:email channel:moderate chat:edit "
                + "chat:read whispers:read whispers:edit channel_editor channel:read:subscriptions"
            ),
            force_verify="true",
        )

    streamer_scopes = ["user_read", "channel:read:subscriptions"]
    """Request these scopes on /streamer_login"""

    @app.route("/streamer_login")
    def streamer_login():
        callback_url = (
            app.bot_config["twitchapi"]["redirect_uri"]
            if "redirect_uri" in app.bot_config["twitchapi"]
            else url_for("authorized", _external=True)
        )
        state = request.args.get("n") or request.referrer or None
        return twitch.authorize(
            callback=callback_url, state=state, scope=" ".join(streamer_scopes), force_verify="true"
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
                log.warning(f"Access denied: reason={request.args['error']}, error={request.args['error_description']}")
            next_url = get_next_url(request, "state")
            return redirect(next_url)
        elif type(resp) is OAuthException:
            log.warning(resp.message)
            log.warning(resp.data)
            log.warning(resp.type)
            next_url = get_next_url(request, "state")
            return redirect(next_url)
        session["twitch_token"] = (resp["access_token"],)

        me_api_response = twitch.get("users")
        if len(me_api_response.data["data"]) < 1:
            return render_template("login_error.html")

        with DBManager.create_session_scope(expire_on_commit=False) as db_session:
            me = User.from_basics(
                db_session,
                UserBasics(
                    me_api_response.data["data"][0]["id"],
                    me_api_response.data["data"][0]["login"],
                    me_api_response.data["data"][0]["display_name"],
                ),
            )
            session["user"] = me.jsonify()

        # bot login
        if me.login == app.bot_config["main"]["nickname"].lower():
            redis = RedisManager.get()
            token_json = UserAccessToken.from_api_response(resp).jsonify()
            redis.set(f"authentication:user-access-token:{me.id}", json.dumps(token_json))
            log.info("Successfully updated bot token in redis")

        # streamer login
        if me.login == app.bot_config["main"]["streamer"].lower():
            # there's a good chance the streamer will later log in using the normal login button.
            # we only update their access token if the returned scope containes the special scopes requested
            # in /streamer_login

            # We use issubset() to say "if the granted scope is a subset of the required scopes", this can be case
            # for example when the bot is running in its own channel and you use /bot_login,
            # then the granted scopes will be a superset of the scopes needed for the streamer.
            # By doing this, both the streamer and bot token will be set if you complete /bot_login with the bot
            # account, and if the bot is running in its own channel.
            if set(resp["scope"]).issubset(set(streamer_scopes)):
                log.info("Streamer logged in but not all scopes present, will not update streamer token")
            else:
                redis = RedisManager.get()
                token_json = UserAccessToken.from_api_response(resp).jsonify()
                redis.set(f"authentication:user-access-token:{me.id}", json.dumps(token_json))
                log.info("Successfully updated streamer token in redis")

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

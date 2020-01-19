import json
import logging

from flask import redirect
from flask import render_template
from flask import request
from flask import session
from flask import url_for
from pajbot.oauth_client_edit import OAuthEdited
from flask_oauthlib.client import OAuthException
from flask_openid import OpenID
import re
import requests

from pajbot.apiwrappers.authentication.access_token import UserAccessToken
from pajbot.managers.db import DBManager
from pajbot.managers.redis import RedisManager
from pajbot.models.user import User, UserBasics

import base64
import time

log = logging.getLogger(__name__)


def init(app):
    oauth = OAuthEdited(app)

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
    try:
        spotify = oauth.remote_app(
            "spotify",
            consumer_key=app.bot_config["spotify"]["client_id"],
            consumer_secret=app.bot_config["spotify"]["client_secret"],
            request_token_params={},
            base_url="https://api.spotify.com/v1/",
            request_token_url=None,
            access_token_method="POST",
            access_token_url="https://accounts.spotify.com/api/token",
            authorize_url="https://accounts.spotify.com/authorize",
        )
    except:
        spotify = None

    try:
        discord = oauth.remote_app(
            "discord",
            consumer_key=app.bot_config["discord"]["client_id"],
            consumer_secret=app.bot_config["discord"]["client_secret"],
            request_token_params={},
            base_url="https://discordapp.com/api",
            request_token_url=None,
            access_token_method="POST",
            access_token_url="https://discordapp.com/api/oauth2/token",
            authorize_url="https://discordapp.com/api/oauth2/authorize",
        )
    except:
        discord = None

    try:
        if (
            "steam" in app.bot_config
            and "secret_key" in app.bot_config["steam"]
            and len(app.bot_config["steam"]["secret_key"]) > 5
        ):
            steam = OpenID(app)
            app.secret_key = app.bot_config["steam"]["secret_key"]
            _steam_id_re = re.compile("steamcommunity.com/openid/id/(.*?)$")
        else:
            steam = None
    except:
        steam = None

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

    streamer_scopes = ["user_read", "channel:read:subscriptions", "bits:read"]  # remove this later
    """Request these scopes on /streamer_login"""
    spotify_scopes = [
        "user-read-playback-state",
        "user-modify-playback-state",
        "user-read-currently-playing",
        "user-read-email",
        "user-read-private",
    ]  # remove this later

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

    if spotify is not None:

        @app.route("/spotify_login")
        def spotify_login():
            if spotify is not None:
                callback_url = (
                    app.bot_config["spotify"]["redirect_uri"]
                    if "redirect_uri" in app.bot_config["spotify"]
                    else url_for("authorized", _external=True)
                )
                state = request.args.get("n") or request.referrer or None
                return spotify.authorize(
                    callback=callback_url, state=state, scope=" ".join(spotify_scopes), force_verify="true"
                )
            return render_template("login_error.html")

    if discord is not None:

        @app.route("/discord_login")
        def discord_login():
            callback_url = (
                app.bot_config["discord"]["redirect_uri"]
                if "redirect_uri" in app.bot_config["discord"]
                else url_for("authorized", _external=True)
            )
            state = request.args.get("n") or request.referrer or None
            return discord.authorize(callback=callback_url, state=state, scope="identify", force_verify="true")

    if steam is not None:

        @app.route("/steam_login")
        @steam.loginhandler
        def steam_login():
            session["next_url"] = request.args.get("n") or request.referrer or None
            return steam.try_login("http://steamcommunity.com/openid")

        @steam.after_login
        def new_user(resp):
            match = _steam_id_re.search(resp.identity_url)
            session["steam_id"] = match.group(1)
            next_url = session["next_url"]
            session.pop("next_url", None)
            return redirect(next_url if next_url else "/")

    @app.route("/login/error")
    def login_error():
        return render_template("login_error.html")

    @app.route("/login/spotify_auth")
    def spotify_auth():
        if spotify is not None:
            try:
                resp = spotify.authorized_response(spotify=True)
            except OAuthException as e:
                log.error(e)
                log.exception("An exception was caught while authorizing")
                next_url = get_next_url(request, "state")
                return redirect(next_url)
            except Exception as e:
                log.error(e)
                log.exception("Unhandled exception while authorizing")
                return render_template("login_error.html")

            session["spotify_token"] = (resp["access_token"],)
            if resp is None:
                if "error" in request.args and "error_description" in request.args:
                    log.warning(
                        f"Access denied: reason={request.args['error']}, error={request.args['error_description']}"
                    )
                next_url = get_next_url(request, "state")
                return redirect(next_url)
            elif type(resp) is OAuthException:
                log.warning(resp.message)
                log.warning(resp.data)
                log.warning(resp.type)
                next_url = get_next_url(request, "state")
                return redirect(next_url)

            data = f'{app.bot_config["spotify"]["client_id"]}:{app.bot_config["spotify"]["client_secret"]}'
            encoded = str(base64.b64encode(data.encode("utf-8")), "utf-8")
            headers = {"Authorization": f"Basic {encoded}"}

            me_api_response = spotify.get("me", headers=headers)

            redis = RedisManager.get()
            token_json = UserAccessToken.from_api_response(resp).jsonify()

            redis.set(f"authentication:spotify-access-token:{me_api_response.data['id']}", json.dumps(token_json))
            redis.set(f"authentication:user-refresh-token:{me_api_response.data['id']}", token_json["refresh_token"])
            log.info(f"Successfully updated spotify token in redis for user {me_api_response.data['id']}")

            next_url = get_next_url(request, "state")
            return redirect(next_url)
        return render_template("login_error.html")

    @app.route("/login/authorized")
    def authorized():
        try:
            resp = twitch.authorized_response()
        except OAuthException as e:
            log.error(e)
            log.exception("An exception was caught while authorizing")
            next_url = get_next_url(request, "state")
            return redirect(next_url)
        except Exception as e:
            log.error(e)
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
        session["twitch_token_expire"] = time.time() + resp["expires_in"] * 0.75

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

            # We use < to say "if the granted scope is a proper subset of the required scopes", this can be case
            # for example when the bot is running in its own channel and you use /bot_login,
            # then the granted scopes will be a superset of the scopes needed for the streamer.
            # By doing this, both the streamer and bot token will be set if you complete /bot_login with the bot
            # account, and if the bot is running in its own channel.
            if set(resp["scope"]) < set(streamer_scopes):
                log.info("Streamer logged in but not all scopes present, will not update streamer token")
            else:
                redis = RedisManager.get()
                token_json = UserAccessToken.from_api_response(resp).jsonify()
                redis.set(f"authentication:user-access-token:{me.id}", json.dumps(token_json))
                log.info("Successfully updated streamer token in redis")

        next_url = get_next_url(request, "state")
        return redirect(next_url)

    if discord is not None:

        @app.route("/login/discord_auth")
        def discord_auth():
            try:
                resp = discord.authorized_response(discord=True)
            except OAuthException as e:
                log.error(e)
                log.exception("An exception was caught while authorizing")
                next_url = get_next_url(request, "state")
                return redirect(next_url)
            except Exception as e:
                log.error(e)
                log.exception("Unhandled exception while authorizing")
                return render_template("login_error.html")
            if resp is None:
                if "error" in request.args and "error_description" in request.args:
                    log.warning(
                        f"Access denied: reason={request.args['error']}, error={request.args['error_description']}"
                    )
                next_url = get_next_url(request, "state")
                return redirect(next_url)
            elif type(resp) is OAuthException:
                log.warning(resp.message)
                log.warning(resp.data)
                log.warning(resp.type)
                next_url = get_next_url(request, "state")
                return redirect(next_url)

            session["discord_token"] = (resp["access_token"],)
            me_api_response = discord.get(url="api/users/@me", discord=True)
            session["discord_id"] = me_api_response["id"]
            session["discord_username"] = me_api_response["username"]
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
        session.pop("twitch_token_expire", None)
        session.pop("steam_id", None)
        session.pop("discord_token", None)
        session.pop("discord_id", None)
        session.pop("discord_username", None)
        next_url = get_next_url(request)
        if next_url.startswith("/admin"):
            next_url = "/"
        return redirect(next_url)

    @app.route("/logout_discord")
    def logout_discord():
        session.pop("discord_token", None)
        session.pop("discord_id", None)
        session.pop("discord_username", None)
        next_url = get_next_url(request)
        if next_url.startswith("/admin"):
            next_url = "/"
        return redirect(next_url)

    @app.route("/logout_steam")
    def logout_steam():
        session.pop("steam_id", None)
        next_url = get_next_url(request)
        if next_url.startswith("/admin"):
            next_url = "/"
        return redirect(next_url)

    @twitch.tokengetter
    def get_twitch_oauth_token():
        return session.get("twitch_token")

    if discord is not None:

        @discord.tokengetter
        def get_discord_oauth_token():
            return session.get("discord_token")

    if spotify is not None:

        @spotify.tokengetter
        def get_token_to_submit():
            return session.get("spotify_token")

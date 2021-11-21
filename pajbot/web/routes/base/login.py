import json
import os
import logging
import base64
import urllib
from json import JSONDecodeError

from flask import redirect
from flask import render_template
from flask import request
from flask import session

from pajbot.managers.db import DBManager
from pajbot.managers.redis import RedisManager
from pajbot.models.user import User

log = logging.getLogger(__name__)


def init(app):
    def twitch_login(scopes, should_verify):
        csrf_token = base64.b64encode(os.urandom(64)).decode("utf-8")
        session["csrf_token"] = csrf_token

        state = {"csrf_token": csrf_token, "return_to": request.args.get("returnTo", None)}

        params = {
            "client_id": app.bot_config["twitchapi"]["client_id"],
            "redirect_uri": app.bot_config["twitchapi"]["redirect_uri"],
            "response_type": "code",
            "scope": " ".join(scopes),
            "state": json.dumps(state),
            "force_verify": "true" if should_verify else "false",
        }

        authorize_url = "https://id.twitch.tv/oauth2/authorize?" + urllib.parse.urlencode(params)
        return redirect(authorize_url)

    bot_scopes = [
        "user:edit",
        "user:read:email",
        "channel:moderate",
        "chat:edit",
        "chat:read",
        "whispers:read",
        "whispers:edit",
        "channel:read:subscriptions",
        "clips:edit",
    ]

    streamer_scopes = ["channel:read:subscriptions", "channel:manage:broadcast"]

    @app.route("/login")
    def login():
        return twitch_login(scopes=[], should_verify=False)

    @app.route("/bot_login")
    def bot_login():
        return twitch_login(scopes=bot_scopes, should_verify=True)

    @app.route("/streamer_login")
    def streamer_login():
        return twitch_login(scopes=streamer_scopes, should_verify=True)

    @app.route("/login/authorized")
    def authorized():
        # First, validate state with CSRF token
        # (CSRF token from request parameter must match token from session)
        state_str = request.args.get("state", None)

        if state_str is None:
            return render_template("login_error.html", return_to="/", detail_msg="State parameter missing"), 400

        try:
            state = json.loads(state_str)
        except JSONDecodeError:
            return render_template("login_error.html", return_to="/", detail_msg="State parameter not valid JSON"), 400

        # we now have a valid state object, we can send the user back to the place they came from
        return_to = state.get("return_to", None)
        if return_to is None:
            # either not present in the JSON at all, or { "return_to": null } (which is the case when you
            # e.g. access /bot_login or /streamer_login directly)
            return_to = "/"

        def login_error(code, detail_msg=None):
            return render_template("login_error.html", return_to=return_to, detail_msg=detail_msg), code

        csrf_token = state.get("csrf_token", None)
        if csrf_token is None:
            return login_error(400, "CSRF token missing from state")

        csrf_token_in_session = session.pop("csrf_token", None)
        if csrf_token_in_session is None:
            return login_error(400, "No CSRF token in session cookie")

        if csrf_token != csrf_token_in_session:
            return login_error(403, "CSRF tokens don't match")

        # determine if we got ?code= or ?error= (success or not)
        # https://tools.ietf.org/html/rfc6749#section-4.1.2
        if "error" in request.args:
            # user was sent back with an error condition
            error_code = request.args["error"]
            optional_error_description = request.args.get("error_description", None)

            if error_code == "access_denied":
                # User pressed "Cancel" button. We don't want to show an error page, instead we will just
                # redirect them to where they were coming from.
                # See also https://tools.ietf.org/html/rfc6749#section-4.1.2.1 for error codes and documentation for them
                return redirect(return_to)

            # All other error conditions, we show an error page.
            if optional_error_description is not None:
                user_detail_msg = f"Error returned from Twitch: {optional_error_description} (code: {error_code})"
            else:
                user_detail_msg = f"Error returned from Twitch (code: {error_code})"

            return login_error(400, user_detail_msg)

        if "code" not in request.args:
            return login_error(400, "No ?code or ?error present on the request")

        # successful authorization
        code = request.args["code"]

        try:
            # gets us an UserAccessToken object
            access_token = app.twitch_id_api.get_user_access_token(code)
        except:
            log.exception("Could not exchange given code for access token with Twitch")
            return login_error(500, "Could not exchange the given code for an access token.")

        user_basics = app.twitch_helix_api.fetch_user_basics_from_authorization(
            (app.api_client_credentials, access_token)
        )

        with DBManager.create_session_scope(expire_on_commit=False) as db_session:
            me = User.from_basics(db_session, user_basics)
            session["user"] = me.jsonify()

        # bot login
        if me.login == app.bot_user.login.lower():
            redis = RedisManager.get()
            redis.set(f"authentication:user-access-token:{me.id}", json.dumps(access_token.jsonify()))
            log.info("Successfully updated bot token in redis")

        # streamer login
        if me.login == app.streamer.login.lower():
            # there's a good chance the streamer will later log in using the normal login button.
            # we only update their access token if the returned scope containes the special scopes requested
            # in /streamer_login

            # We use < to say "if the granted scope is a proper subset of the required scopes", this can be case
            # for example when the bot is running in its own channel and you use /bot_login,
            # then the granted scopes will be a superset of the scopes needed for the streamer.
            # By doing this, both the streamer and bot token will be set if you complete /bot_login with the bot
            # account, and if the bot is running in its own channel.
            if set(access_token.scope) < set(streamer_scopes):
                log.info("Streamer logged in but not all scopes present, will not update streamer token")
            else:
                redis = RedisManager.get()
                redis.set(f"authentication:user-access-token:{me.id}", json.dumps(access_token.jsonify()))
                log.info("Successfully updated streamer token in redis")

        return redirect(return_to)

    @app.route("/logout")
    def logout():
        session.pop("user", None)

        return_to = request.args.get("returnTo", "/")
        if return_to.startswith("/admin"):
            return_to = "/"

        return redirect(return_to)

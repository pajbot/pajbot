import logging
import uuid

import flask
from flask import redirect
from flask import session
from flask import url_for
from flask_oauthlib.client import OAuth
from flask_oauthlib.client import OAuthException
from flask_restful import reqparse
from flask_restful import Resource

import pajbot.web.utils
from pajbot.web import app

log = logging.getLogger(__name__)


def has_streamtip():
    if 'streamtip' not in app.bot_config:
        return False

    if 'client_id' not in app.bot_config['streamtip']:
        return False

    if 'client_secret' not in app.bot_config['streamtip']:
        return False

    return True


def init(api):
    if not has_streamtip():
        log.info('Streamtip support not set up')
        log.info('Check out the install/config.example.ini and set up the client_id and client_secret under the [streamtip] section')
        return

    oauth = OAuth(api)

    streamtip = oauth.remote_app(
            'streamtip',
            consumer_key=app.bot_config['streamtip']['client_id'],
            consumer_secret=app.bot_config['streamtip']['client_secret'],
            base_url='https://streamtip.com/api/',
            request_token_params={
                'scope': [
                    'donations.read',
                    'donations.create',
                    ],
                },
            request_token_url=None,
            access_token_headers={
                'User-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/56.0.2924.87 Safari/537.36',
                },
            access_token_method='POST',
            access_token_url='https://streamtip.com/api/oauth2/token',
            authorize_url='https://streamtip.com/api/oauth2/authorize',
            )

    class StreamtipIndex(Resource):
        def get(self):
            return redirect(url_for('streamtiplogin'))

    class StreamtipLogin(Resource):
        def get(self):
            callback = url_for('streamtiploginauthorized', _external=True)
            return streamtip.authorize(callback=callback, state=uuid.uuid4())

    class StreamtipLoginAuthorized(Resource):
        def __init__(self):
            super().__init__()

            self.parser = reqparse.RequestParser()
            self.parser.add_argument('error')
            self.parser.add_argument('error_description')

        def get(self):
            try:
                resp = streamtip.authorized_response()
            except OAuthException:
                log.exception('Exception caught while authorizing with streamtip')
                return 'error 1'
            except:
                log.exception('Unhandled exception caught while authorizing with streamtip')
                return 'error 2'

            if resp is None:
                args = self.parser.parse_args()
                log.warn('Access denied: reason={}, error={}'.format(args['error'], args['error_description']))
                return args['error']

            if type(resp) is OAuthException:
                log.warn(resp.message)
                log.warn(resp.data)
                log.warn(resp.type)
                return 'error 3'

            access_token = resp['access_token']
            session['streamtip_token'] = (access_token, )

            log.debug(resp)

            me = streamtip.get('me')

            if me.data['user']['provider'] == 'twitch':
                if me.data['user']['name'] in ('pajlada', app.bot_config['main']['streamer']):
                    password = pajbot.web.utils.create_pleblist_login(app.bot_config)
                    resp = flask.make_response(redirect('/pleblist/host'))
                    resp.set_cookie('password', password)
                    resp.set_cookie('streamtip_access_token', access_token)
                    return resp

            return 'you can\'t use this pleblist'

    @streamtip.tokengetter
    def get_streamtip_oauth_token():
        return session.get('streamtip_token')

    api.add_resource(StreamtipIndex, '/streamtip')
    api.add_resource(StreamtipLogin, '/streamtip/login')
    api.add_resource(StreamtipLoginAuthorized, '/streamtip/login/authorized')

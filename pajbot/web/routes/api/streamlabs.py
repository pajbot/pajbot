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


def has_streamlabs():
    if 'streamlabs' not in app.bot_config:
        return False

    if 'client_id' not in app.bot_config['streamlabs']:
        return False

    if 'client_secret' not in app.bot_config['streamlabs']:
        return False

    return True


def init(api):
    if not has_streamlabs():
        log.info('Streamlabs support not set up')
        log.info('Check out the install/config.example.ini and set up the client_id and client_secret under the [streamlabs] section')
        return

    oauth = OAuth(api)

    streamlabs = oauth.remote_app(
            'streamlabs',
            consumer_key=app.bot_config['streamlabs']['client_id'],
            consumer_secret=app.bot_config['streamlabs']['client_secret'],
            base_url='https://streamlabs.com/api/v1.0/',
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
            access_token_url='https://streamlabs.com/api/v1.0/token',
            authorize_url='https://streamlabs.com/api/v1.0/authorize',
            )

    class StreamlabsIndex(Resource):
        def get(self):
            return redirect(url_for('streamlabslogin'))

    class StreamlabsLogin(Resource):
        def get(self):
            callback = url_for('streamlabsloginauthorized', _external=True)
            return streamlabs.authorize(callback=callback, state=uuid.uuid4())

    class StreamlabsLoginAuthorized(Resource):
        def __init__(self):
            super().__init__()

            self.parser = reqparse.RequestParser()
            self.parser.add_argument('error')
            self.parser.add_argument('error_description')

        def get(self):
            try:
                resp = streamlabs.authorized_response()
            except OAuthException:
                log.exception('Exception caught while authorizing with streamlabs')
                return 'error 1'
            except:
                log.exception('Unhandled exception caught while authorizing with streamlabs')
                return 'error 2'

            args = self.parser.parse_args()

            if resp is None:
                log.warn('Access denied: reason={}, error={}'.format(args['error'], args['error_description']))
                return args['error']

            if type(resp) is OAuthException:
                log.warn(resp.message)
                log.warn(resp.data)
                log.warn(resp.type)
                return 'error 3'

            session['streamlabs_token'] = (resp['access_token'], )

            me = streamlabs.get('user')

            log.info(me)
            log.info(me.data)
            log.info(me.data['twitch'])
            log.info(me.data['twitch']['name'])

            if me.data['twitch']['name'] in ('pajlada', app.bot_config['main']['streamer']):
                password = pajbot.web.utils.create_pleblist_login(app.bot_config)
                resp = flask.make_response(flask.jsonify({'password': password}))
                resp.set_cookie('password', password)
                return resp

            return 'you can\'t use this pleblist'

    @streamlabs.tokengetter
    def get_streamlabs_oauth_token():
        return session.get('streamlabs_token')

    api.add_resource(StreamlabsIndex, '/streamlabs')
    api.add_resource(StreamlabsLogin, '/streamlabs/login')
    api.add_resource(StreamlabsLoginAuthorized, '/streamlabs/login/authorized')

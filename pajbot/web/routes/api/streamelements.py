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


def has_streamelements():
    if 'streamelements' not in app.bot_config:
        return False

    if 'client_id' not in app.bot_config['streamelements']:
        return False

    if 'client_secret' not in app.bot_config['streamelements']:
        return False

    return True


def init(api):
    if not has_streamelements():
        log.info('StreamElements support not set up.')
        log.info('Check out the install/config.example.ini and set up the client_id and client_secret under the [streamelements] section')
        return

    oauth = OAuth(api)

    streamelements = oauth.remote_app(
            'streamelements',
            consumer_key=app.bot_config['streamelements']['client_id'],
            consumer_secret=app.bot_config['streamelements']['client_secret'],
            base_url='https://api.streamelements.com/',
            request_token_url=None,
            access_token_method='POST',
            access_token_url='https://api.streamelements.com/oauth2/token',
            authorize_url='https://streamelements.com/oauth2/authorize',
            )

    class StreamElementsIndex(Resource):
        def get(self):
            return redirect(url_for('streamelementslogin'))

    class StreamElementsLogin(Resource):
        def get(self):
            callback = url_for('streamelementsloginauthorized', _external=True)
            return streamelements.authorize(callback=callback, state=uuid.uuid4())

    class StreamElementsLoginAuthorized(Resource):
        def __init__(self):
            super().__init__()

            self.parser = reqparse.RequestParser()
            self.parser.add_argument('error')
            self.parser.add_argument('error_description')

        def get(self):
            try:
                resp = streamelements.authorized_response()
            except OAuthException:
                log.exception('Exception caught while authorizing with streamelements')
                return 'error 1'
            except:
                log.exception('Unhandled exception caught while authorizing with streamelements')
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

            access_token = resp['access_token']
            session['streamelements_token'] = (access_token, )

            me = streamelements.get('kappa/v1/users/me')

            if me.data['username'] in ('pajlada', app.bot_config['main']['streamer']):
                password = pajbot.web.utils.create_pleblist_login(app.bot_config)
                resp = flask.make_response(redirect('/pleblist/host'))
                resp.set_cookie('password', password)
                resp.set_cookie('streamelements_access_token', access_token)
                return resp

            return 'you can\'t use this pleblist'

    @streamelements.tokengetter
    def get_streamelements_oauth_token():
        return session.get('streamelements_token')

    def change_streamelements_header(uri, headers, body):
        auth = headers.get('Authorization')
        if auth:
            auth = auth.replace('Bearer', 'OAuth')
            headers['Authorization'] = auth
        return uri, headers, body

    streamelements.pre_request = change_streamelements_header

    api.add_resource(StreamElementsIndex, '/streamelements')
    api.add_resource(StreamElementsLogin, '/streamelements/login')
    api.add_resource(StreamElementsLoginAuthorized, '/streamelements/login/authorized')

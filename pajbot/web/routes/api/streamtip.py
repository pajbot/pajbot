import logging

import flask
import requests
from flask import redirect
from flask_restful import reqparse
from flask_restful import Resource

import pajbot.web.utils
from pajbot.web import app

log = logging.getLogger(__name__)


class APIStreamtipOAuth(Resource):
    def __init__(self):
        super().__init__()

        self.post_parser = reqparse.RequestParser()
        self.post_parser.add_argument('code', trim=True, required=True)

    def get(self):
        args = self.post_parser.parse_args()

        if 'streamtip' not in app.bot_config:
            return {
                    'error': 'Config not set up properly.'
                    }, 500

        payload = {
                'client_id': app.bot_config['streamtip']['client_id'],
                'client_secret': app.bot_config['streamtip']['client_secret'],
                'grant_type': 'authorization_code',
                'redirect_uri': app.bot_config['streamtip']['redirect_uri'],
                'code': args['code'],
                }

        r = requests.post('https://streamtip.com/api/oauth2/token', data=payload)

        return redirect('/pleblist/host/#STREAMTIP{}'.format(r.json()['access_token']), 303)


class APIStreamtipValidate(Resource):
    def __init__(self):
        super().__init__()

        self.post_parser = reqparse.RequestParser()
        self.post_parser.add_argument('access_token', trim=True, required=True)

    def post(self):
        args = self.post_parser.parse_args()

        if 'streamtip' not in app.bot_config:
            return {
                    'error': 'Config not set up properly.'
                    }, 500

        r = requests.get('https://streamtip.com/api/me?access_token={}'.format(args['access_token']))

        valid_streamtip_ids = [app.bot_config['web']['pleblist_streamtip_userid'], '54c1354fe6b5a0f83c5d2ab1']

        if r.json()['user']['_id'] not in valid_streamtip_ids:
            return {
                    'error': 'Invalid user ID'
                    }, 400

        password = pajbot.web.utils.create_pleblist_login(app.bot_config)
        resp = flask.make_response(flask.jsonify({'password': password}))
        resp.set_cookie('password', password)
        return resp


def init(api):
    api.add_resource(APIStreamtipOAuth, '/streamtip/oauth')
    api.add_resource(APIStreamtipValidate, '/streamtip/validate')

import logging

import flask
import requests
from flask import redirect
from flask_restful import reqparse
from flask_restful import Resource

import pajbot.web.utils
from pajbot.web import app

log = logging.getLogger(__name__)


def has_twitchalerts():
    if 'twitchalerts' not in app.bot_config:
        return False

    if 'client_id' not in app.bot_config['twitchalerts']:
        return False

    if 'client_secret' not in app.bot_config['twitchalerts']:
        return False

    return True


class APITwitchAlertsOAuth(Resource):
    def __init__(self):
        super().__init__()

        self.post_parser = reqparse.RequestParser()
        self.post_parser.add_argument('code', trim=True, required=True)

    def get(self):
        args = self.post_parser.parse_args()

        if 'twitchalerts' not in app.bot_config:
            return {
                    'error': 'Config not set up properly.'
                    }, 500

        payload = {
                'client_id': app.bot_config['twitchalerts']['client_id'],
                'client_secret': app.bot_config['twitchalerts']['client_secret'],
                'grant_type': 'authorization_code',
                'redirect_uri': app.bot_config['twitchalerts']['redirect_uri'],
                'code': args['code'],
                }

        r = requests.post('https://www.twitchalerts.com/api/v1.0/token', data=payload)

        return redirect('/pleblist/host/#TWITCHALERTS{}'.format(r.json()['access_token']), 303)


class APITwitchAlertsValidate(Resource):
    def shared(self):
        password = pajbot.web.utils.create_pleblist_login(app.bot_config)
        resp = flask.make_response(flask.jsonify({'password': password}))
        resp.set_cookie('password', password)
        return resp

    @pajbot.web.utils.requires_level(1000)
    def post(self, **options):
        return self.shared()

    @pajbot.web.utils.requires_level(1000)
    def get(self, **options):
        return self.shared()


def init(api):
    pass

import logging

from flask_restful import reqparse
from flask_restful import Resource

import pajbot.modules
import pajbot.utils
import pajbot.web.utils
from pajbot.managers import AdminLogManager
from pajbot.managers import DBManager
from pajbot.models.banphrase import Banphrase
from pajbot.models.sock import SocketClientManager

log = logging.getLogger(__name__)


class APIBanphraseRemove(Resource):
    @pajbot.web.utils.requires_level(500)
    def get(self, banphrase_id, **options):
        with DBManager.create_session_scope() as db_session:
            banphrase = db_session.query(Banphrase).filter_by(id=banphrase_id).one_or_none()
            if banphrase is None:
                return {'error': 'Invalid banphrase ID'}, 404
            AdminLogManager.post('Banphrase removed', options['user'], banphrase.phrase)
            db_session.delete(banphrase)
            db_session.delete(banphrase.data)
            SocketClientManager.send('banphrase.remove', {'id': banphrase.id})
            return {'success': 'good job'}, 200


class APIBanphraseToggle(Resource):
    def __init__(self):
        super().__init__()

        self.post_parser = reqparse.RequestParser()
        self.post_parser.add_argument('new_state', required=True)

    @pajbot.web.utils.requires_level(500)
    def post(self, row_id, **options):
        args = self.post_parser.parse_args()

        try:
            new_state = int(args['new_state'])
        except (ValueError, KeyError):
            return {'error': 'Invalid `new_state` parameter.'}, 400

        with DBManager.create_session_scope() as db_session:
            row = db_session.query(Banphrase).filter_by(id=row_id).one_or_none()

            if not row:
                return {
                        'error': 'Banphrase with this ID not found'
                        }, 404

            row.enabled = True if new_state == 1 else False
            db_session.commit()
            payload = {
                    'id': row.id,
                    'new_state': row.enabled,
                    }
            AdminLogManager.post('Banphrase toggled',
                    options['user'],
                    'Enabled' if row.enabled else 'Disabled',
                    row.phrase)
            SocketClientManager.send('banphrase.update', payload)
            return {'success': 'successful toggle', 'new_state': new_state}


def init(api):
    api.add_resource(APIBanphraseRemove, '/banphrases/remove/<int:banphrase_id>')
    api.add_resource(APIBanphraseToggle, '/banphrases/toggle/<int:row_id>')

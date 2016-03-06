import logging

from pajbot.models.banphrase import Banphrase, BanphraseData
from pajbot.models.db import DBManager
from pajbot.models.sock import SocketClientManager
from pajbot.web.utils import requires_level

from flask import abort
from flask import redirect
from flask import render_template
from flask import request
from flask import session
from sqlalchemy.orm import joinedload

log = logging.getLogger(__name__)

def init(page):
    @page.route('/banphrases/')
    @requires_level(500)
    def banphrases(**options):
        with DBManager.create_session_scope() as db_session:
            banphrases = db_session.query(Banphrase).options(joinedload(Banphrase.data).joinedload(BanphraseData.user), joinedload(Banphrase.data).joinedload(BanphraseData.user2)).all()
            return render_template('admin/banphrases.html',
                    banphrases=banphrases)

    @page.route('/banphrases/create', methods=['GET', 'POST'])
    @requires_level(500)
    def banphrases_create(**options):
        session.pop('banphrase_created_id', None)
        session.pop('banphrase_edited_id', None)
        if request.method == 'POST':
            id = None
            try:
                if 'id' in request.form:
                    id = int(request.form['id'])
                name = request.form['name'].strip()
                permanent = request.form.get('permanent', 'off')
                warning = request.form.get('warning', 'off')
                notify = request.form.get('notify', 'off')
                case_sensitive = request.form.get('case_sensitive', 'off')
                sub_immunity = request.form.get('sub_immunity', 'off')
                length = int(request.form['length'])
                phrase = request.form['phrase'].strip()
                operator = request.form['operator'].strip().lower()
            except (KeyError, ValueError):
                abort(403)

            permanent = True if permanent == 'on' else False
            warning = True if warning == 'on' else False
            notify = True if notify == 'on' else False
            case_sensitive = True if case_sensitive == 'on' else False
            sub_immunity = True if sub_immunity == 'on' else False

            if len(name) == 0:
                abort(403)

            if len(phrase) == 0:
                abort(403)

            if length < 0 or length > 1209600:
                abort(403)

            valid_operators = ['contains', 'startswith', 'endswith']
            if operator not in valid_operators:
                abort(403)

            user = options.get('user', None)

            if user is None:
                abort(403)

            options = {
                    'name': name,
                    'phrase': phrase,
                    'permanent': permanent,
                    'warning': warning,
                    'notify': notify,
                    'case_sensitive': case_sensitive,
                    'sub_immunity': sub_immunity,
                    'length': length,
                    'added_by': user.id,
                    'edited_by': user.id,
                    'operator': operator,
                    }

            if id is None:
                banphrase = Banphrase(**options)
                banphrase.data = BanphraseData(banphrase.id, added_by=options['added_by'])

            with DBManager.create_session_scope(expire_on_commit=False) as db_session:
                if id is not None:
                    banphrase = db_session.query(Banphrase).options(joinedload(Banphrase.data)).filter_by(id=id).one_or_none()
                    if banphrase is None:
                        return redirect('/admin/banphrases/', 303)
                    banphrase.set(**options)
                    banphrase.data.set(edited_by=options['edited_by'])
                    log.info('Updated banphrase ID {} by user ID {}'.format(banphrase.id, options['edited_by']))
                else:
                    db_session.add(banphrase)
                    db_session.add(banphrase.data)
                    log.info('Added a new banphrase by user ID {}'.format(options['added_by']))

            SocketClientManager.send('banphrase.update', {'banphrase_id': banphrase.id})
            if id is None:
                session['banphrase_created_id'] = banphrase.id
            else:
                session['banphrase_edited_id'] = banphrase.id
            return redirect('/admin/banphrases/', 303)
        else:
            return render_template('admin/create_banphrase.html')

    @page.route('/banphrases/edit/<banphrase_id>')
    @requires_level(500)
    def banphrases_edit(banphrase_id, **options):
        with DBManager.create_session_scope() as db_session:
            banphrase = db_session.query(Banphrase).filter_by(id=banphrase_id).one_or_none()

            if banphrase is None:
                return render_template('admin/banphrase_404.html'), 404

            return render_template('admin/create_banphrase.html',
                    banphrase=banphrase)

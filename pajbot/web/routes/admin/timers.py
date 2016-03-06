import logging

from pajbot.models.db import DBManager
from pajbot.models.sock import SocketClientManager
from pajbot.models.timer import Timer
from pajbot.web.utils import requires_level

from flask import abort
from flask import redirect
from flask import render_template
from flask import request
from flask import session

log = logging.getLogger(__name__)


def init(page):
    @page.route('/timers/')
    @requires_level(500)
    def timers(**options):
        with DBManager.create_session_scope() as db_session:
            return render_template('admin/timers.html',
                    timers=db_session.query(Timer).all(),
                    created=session.pop('timer_created_id', None),
                    edited=session.pop('timer_edited_id', None))

    @page.route('/timers/edit/<timer_id>')
    @requires_level(500)
    def timers_edit(timer_id, **options):
        with DBManager.create_session_scope() as db_session:
            timer = db_session.query(Timer).filter_by(id=timer_id).one_or_none()

            if timer is None:
                return render_template('admin/timer_404.html'), 404

            return render_template('admin/create_timer.html',
                    timer=timer)

    @page.route('/timers/create', methods=['GET', 'POST'])
    @requires_level(500)
    def timers_create(**options):
        session.pop('timer_created_id', None)
        session.pop('timer_edited_id', None)
        if request.method == 'POST':
            id = None
            try:
                if 'id' in request.form:
                    id = int(request.form['id'])
                name = request.form['name'].strip()
                interval_online = int(request.form['interval_online'])
                interval_offline = int(request.form['interval_offline'])
                message_type = request.form['message_type']
                message = request.form['message'].strip()
            except (KeyError, ValueError):
                abort(403)

            if interval_online < 0 or interval_offline < 0:
                abort(403)

            if message_type not in ['say', 'me']:
                abort(403)

            if len(message) == 0:
                abort(403)

            options = {
                    'name': name,
                    'interval_online': interval_online,
                    'interval_offline': interval_offline,
                    }

            action = {
                    'type': message_type,
                    'message': message
                    }
            options['action'] = action

            if id is None:
                timer = Timer(**options)

            with DBManager.create_session_scope(expire_on_commit=False) as db_session:
                if id is not None:
                    timer = db_session.query(Timer).filter_by(id=id).one_or_none()
                    if timer is None:
                        return redirect('/admin/timers/', 303)
                    timer.set(**options)
                else:
                    db_session.add(timer)

            SocketClientManager.send('timer.update', {'timer_id': timer.id})
            if id is None:
                session['timer_created_id'] = timer.id
            else:
                session['timer_edited_id'] = timer.id
            return redirect('/admin/timers/', 303)
        else:
            return render_template('admin/create_timer.html')

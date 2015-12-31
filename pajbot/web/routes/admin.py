import datetime
import base64
import binascii
import logging
import collections

from pajbot.tbutil import find
from pajbot.web.utils import requires_level
from pajbot.models.banphrase import Banphrase, BanphraseData
from pajbot.models.command import Command, CommandData, CommandManager
from pajbot.models.module import ModuleManager, Module
from pajbot.models.timer import Timer
from pajbot.models.linkchecker import BlacklistedLink
from pajbot.models.linkchecker import WhitelistedLink
from pajbot.models.user import User
from pajbot.models.sock import SocketClientManager
from pajbot.models.db import DBManager
from pajbot.modules.predict import PredictionRun, PredictionRunEntry

import requests
from flask import Blueprint
from flask import jsonify
from flask import make_response
from flask import request
from flask import redirect
from flask import render_template
from flask import session
from flask import abort
from flask.ext.scrypt import generate_password_hash
from flask.ext.scrypt import check_password_hash
from sqlalchemy import func
from sqlalchemy import and_
from sqlalchemy.orm import joinedload

page = Blueprint('admin', __name__, url_prefix='/admin')

log = logging.getLogger(__name__)


@page.route('/')
@requires_level(500)
def home(**options):
    return render_template('admin/home.html')

@page.route('/banphrases/')
@requires_level(500)
def banphrases(**options):
    with DBManager.create_session_scope() as db_session:
        banphrases = db_session.query(Banphrase).options(joinedload(Banphrase.data).joinedload(BanphraseData.user)).all()
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
            length = int(request.form['length'])
            phrase = request.form['phrase'].strip()
        except (KeyError, ValueError):
            abort(403)

        permanent = True if permanent == 'on' else False
        warning = True if warning == 'on' else False
        notify = True if notify == 'on' else False
        case_sensitive = True if case_sensitive == 'on' else False

        if len(name) == 0:
            abort(403)

        if len(phrase) == 0:
            abort(403)

        if length < 0 or length > 1209600:
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
                'length': length,
                'added_by': user.id,
                }

        if id is None:
            banphrase = Banphrase(**options)
            banphrase.data = BanphraseData(banphrase.id, added_by=options['added_by'])

        with DBManager.create_session_scope(expire_on_commit=False) as db_session:
            if id is not None:
                banphrase = db_session.query(Banphrase).filter_by(id=id).one_or_none()
                if banphrase is None:
                    return redirect('/admin/banphrases/', 303)
                banphrase.set(**options)
            else:
                log.info('adding...')
                db_session.add(banphrase)
                log.info('adding data..')
                db_session.add(banphrase.data)
                log.info('should commit now...')
        log.info('commited')

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

@page.route('/links/blacklist/')
@requires_level(500)
def links_blacklist(**options):
    with DBManager.create_session_scope() as db_session:
        links = db_session.query(BlacklistedLink).filter_by().all()
        return render_template('admin/links_blacklist.html',
                links=links)

@page.route('/links/whitelist/')
@requires_level(500)
def links_whitelist(**options):
    with DBManager.create_session_scope() as db_session:
        links = db_session.query(WhitelistedLink).filter_by().all()
        return render_template('admin/links_whitelist.html',
                links=links)

@page.route('/commands/')
@requires_level(500)
def commands(**options):
    from pajbot.models.command import CommandManager
    from pajbot.models.module import ModuleManager
    bot_commands = CommandManager(
            socket_manager=None,
            module_manager=ModuleManager(None).load(),
            bot=None).load(enabled=None)

    bot_commands_list = bot_commands.parse_for_web()
    custom_commands = []
    point_commands = []
    moderator_commands = []

    for command in bot_commands_list:
        if command.id is None:
            continue
        if command.level > 100 or command.mod_only:
            moderator_commands.append(command)
        elif command.cost > 0:
            point_commands.append(command)
        else:
            custom_commands.append(command)

    return render_template('admin/commands.html',
            custom_commands=sorted(custom_commands, key=lambda f: f.command),
            point_commands=sorted(point_commands, key=lambda a: (a.cost, a.command)),
            moderator_commands=sorted(moderator_commands, key=lambda c: (c.level if c.mod_only is False else 500, c.command)),
            created=session.pop('command_created_id', None),
            edited=session.pop('command_edited_id', None))

@page.route('/commands/edit/<command_id>')
@requires_level(500)
def commands_edit(command_id, **options):
    with DBManager.create_session_scope() as db_session:
        command = db_session.query(Command).filter_by(id=command_id).one_or_none()

        if command is None:
            return render_template('admin/command_404.html'), 404

        return render_template('admin/edit_command.html',
                command=command,
                user=options.get('user', None))

@page.route('/commands/create', methods=['GET', 'POST'])
@requires_level(500)
def commands_create(**options):
    session.pop('command_created_id', None)
    session.pop('command_edited_id', None)
    if request.method == 'POST':
        if 'aliases' not in request.form:
            abort(403)
        alias_str = request.form.get('aliases', '').replace('!', '').lower()
        delay_all = request.form.get('cd', Command.DEFAULT_CD_ALL)
        delay_user = request.form.get('usercd', Command.DEFAULT_CD_USER)
        level = request.form.get('level', Command.DEFAULT_LEVEL)
        cost = request.form.get('cost', 0)

        try:
            delay_all = int(delay_all)
            delay_user = int(delay_user)
            level = int(level)
            cost = int(cost)
        except ValueError:
            abort(403)

        if len(alias_str) == 0:
            abort(403)
        if delay_all < 0 or delay_all > 9999:
            abort(403)
        if delay_user < 0 or delay_user > 9999:
            abort(403)
        if level < 0 or level > 2000:
            abort(403)
        if cost < 0 or cost > 9999999:
            abort(403)

        options = {
                'delay_all': delay_all,
                'delay_user': delay_user,
                'level': level,
                'cost': cost,
                }

        valid_action_types = ['say', 'me', 'whisper', 'reply']
        action_type = request.form.get('reply', 'say').lower()
        if action_type not in valid_action_types:
            abort(403)

        response = request.form.get('response', '')
        if len(response) == 0:
            abort(403)

        action = {
                'type': action_type,
                'message': response
                }
        options['action'] = action

        command_manager = CommandManager(
                socket_manager=None,
                module_manager=ModuleManager(None).load(),
                bot=None).load(enabled=None)

        command_aliases = []

        for alias, command in command_manager.items():
            command_aliases.append(alias)
            if command.command and len(command.command) > 0:
                command_aliases.extend(command.command.split('|'))

        command_aliases = set(command_aliases)

        alias_str = alias_str.replace(' ', '').replace('!', '').lower()
        alias_list = alias_str.split('|')

        alias_list = [alias for alias in alias_list if len(alias) > 0]

        if len(alias_list) == 0:
            return render_template('admin/create_command_fail.html')

        for alias in alias_list:
            if alias in command_aliases:
                return render_template('admin/create_command_fail.html')

        alias_str = '|'.join(alias_list)

        command = Command(command=alias_str, **options)
        command.data = CommandData(command.id)
        with DBManager.create_session_scope(expire_on_commit=False) as db_session:
            db_session.add(command)
            db_session.add(command.data)
            db_session.commit()
            db_session.expunge(command)
            db_session.expunge(command.data)

        SocketClientManager.send('command.update', {'command_id': command.id})
        session['command_created_id'] = command.id
        return redirect('/admin/commands/', 303)
    else:
        return render_template('admin/create_command.html')

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

@page.route('/moderators/')
@requires_level(500)
def moderators(**options):
    with DBManager.create_session_scope() as db_session:
        moderator_users = db_session.query(User).filter(User.level > 100).order_by(User.level.desc()).all()
        userlists = collections.OrderedDict()
        userlists['Admins'] = list(filter(lambda user: user.level >= 2000, moderator_users))
        userlists['Super Moderators/Broadcaster'] = list(filter(lambda user: user.level >= 1000 and user.level < 2000, moderator_users))
        userlists['Moderators'] = list(filter(lambda user: user.level >= 500 and user.level < 1000, moderator_users))
        userlists['Notables/Helpers'] = list(filter(lambda user: user.level >= 101 and user.level < 500, moderator_users))
        return render_template('admin/moderators.html',
                userlists=userlists)

@page.route('/modules/')
@requires_level(500)
def modules(**options):
    module_manager = ModuleManager(None).load(do_reload=False)
    for module in module_manager.all_modules:
        module.db_module = None
    with DBManager.create_session_scope() as db_session:
        for db_module in db_session.query(Module):
            module = find(lambda m: m.ID == db_module.id, module_manager.all_modules)
            if module:
                module.db_module = db_module

        return render_template('admin/modules.html',
                modules=module_manager.all_modules)

@page.route('/modules/edit/<module_id>', methods=['GET', 'POST'])
@requires_level(500)
def modules_edit(module_id, **options):
    module_manager = ModuleManager(None).load(do_reload=False)
    current_module = find(lambda m: m.ID == module_id, module_manager.all_modules)

    if current_module is None:
        return render_template('admin/module_404.html'), 404

    if request.method == 'POST':
        form_values = {key: value for key, value in request.form.items()}
        res = current_module.parse_settings(**form_values)
        if res is False:
            return render_template('admin/module_404.html'), 404

        with DBManager.create_session_scope() as db_session:
            db_module = db_session.query(Module).filter_by(id=module_id).one_or_none()
            if db_module is None:
                return render_template('admin/module_404.html'), 404

            current_module.db_module = db_module

            return render_template('admin/configure_module.html',
                    module=current_module)
        pass
    else:
        with DBManager.create_session_scope() as db_session:
            db_module = db_session.query(Module).filter_by(id=module_id).one_or_none()
            if db_module is None:
                return render_template('admin/module_404.html'), 404

            current_module.db_module = db_module

            return render_template('admin/configure_module.html',
                    module=current_module)

@page.route('/predictions/')
@requires_level(500)
def predictions(**options):
    with DBManager.create_session_scope() as db_session:
        predictions = db_session.query(PredictionRun).order_by(PredictionRun.started.desc()).all()

        for prediction in predictions:
            prediction.num_entries = db_session.query(PredictionRunEntry).filter_by(prediction_run_id=prediction.id).count()
            pass

        return render_template('admin/predictions.html',
                predictions=predictions)

@page.route('/predictions/view/<prediction_run_id>')
@requires_level(500)
def predictions_view(prediction_run_id, **options):
    with DBManager.create_session_scope() as db_session:
        prediction = db_session.query(PredictionRun).filter_by(id=prediction_run_id).one_or_none()
        if prediction is None:
            abort(404)

        entries = db_session.query(PredictionRunEntry).options(joinedload(PredictionRunEntry.user)).filter_by(prediction_run_id=prediction_run_id).order_by(PredictionRunEntry.prediction.asc()).all()
        prediction.num_entries = len(entries)

        return render_template('admin/predictions_view.html',
                prediction=prediction,
                entries=entries)

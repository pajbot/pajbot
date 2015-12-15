import datetime
import base64
import binascii
import logging

from tyggbot.web.utils import requires_level
from tyggbot.models.filter import Filter
from tyggbot.models.command import Command
from tyggbot.models.linkchecker import BlacklistedLink
from tyggbot.models.linkchecker import WhitelistedLink
from tyggbot.models.user import User
from tyggbot.models.db import DBManager

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

page = Blueprint('admin', __name__, url_prefix='/admin')

log = logging.getLogger(__name__)


@page.route('/')
@requires_level(500)
def home():
    return render_template('admin/home.html')

@page.route('/banphrases/')
@requires_level(500)
def banphrases():
    with DBManager.create_session_scope() as db_session:
        banphrases = db_session.query(Filter).filter_by(enabled=True, type='banphrase').all()
        return render_template('admin/banphrases.html',
                banphrases=banphrases)

@page.route('/links/blacklist/')
@requires_level(500)
def links_blacklist():
    with DBManager.create_session_scope() as db_session:
        links = db_session.query(BlacklistedLink).filter_by().all()
        return render_template('admin/links_blacklist.html',
                links=links)

@page.route('/links/whitelist/')
@requires_level(500)
def links_whitelist():
    with DBManager.create_session_scope() as db_session:
        links = db_session.query(WhitelistedLink).filter_by().all()
        return render_template('admin/links_whitelist.html',
                links=links)

@page.route('/commands/')
@requires_level(500)
def commands():
    from tyggbot.models.command import CommandManager
    bot_commands = CommandManager(None).load()

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
            moderator_commands=sorted(moderator_commands, key=lambda c: (c.level if c.mod_only is False else 500, c.command)))

@page.route('/commands/edit/<command_id>')
@requires_level(500)
def commands_edit(command_id):
    with DBManager.create_session_scope() as db_session:
        command = db_session.query(Command).filter_by(id=command_id).one_or_none()

        if command is None:
            return render_template('admin/command_404.html'), 404

        return render_template('admin/edit_command.html', command=command)

#!/usr/bin/env python3

import argparse
import os
import configparser
import json
import math
import logging
# import random
import datetime

from tyggbot.web.models import api
from tyggbot.web.models import errors
from tyggbot.models.db import DBManager
from tyggbot.tbutil import load_config, init_logging, time_nonclass_method
from tyggbot.models.deck import Deck
from tyggbot.models.user import User
from tyggbot.models.stream import Stream, StreamChunkHighlight
from tyggbot.models.webcontent import WebContent

import markdown
from apscheduler.schedulers.background import BackgroundScheduler
from flask import Flask
from flask import render_template
from flask import Markup
from flask import redirect
# from flask import make_response
# from flask import jsonify
from sqlalchemy import func, cast, Date

init_logging('tyggbot')
log = logging.getLogger('tyggbot')

cron = BackgroundScheduler(daemon=True)

cron.start()

app = Flask(__name__)
app._static_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static')
app.register_blueprint(api.page)

config = configparser.ConfigParser()

parser = argparse.ArgumentParser(description='start the web app')
parser.add_argument('--config', default='config.ini')
parser.add_argument('--host', default='0.0.0.0')
parser.add_argument('--port', type=int, default=2325)
parser.add_argument('--debug', dest='debug', action='store_true')
parser.add_argument('--no-debug', dest='debug', action='store_false')
parser.set_defaults(debug=False)

args = parser.parse_args()

config = load_config(args.config)

DBManager.init(config['main']['db'])

session = DBManager.create_session()
num_decks = session.query(func.count(Deck.id)).scalar()
custom_web_content = {}
for web_content in session.query(WebContent).filter(WebContent.content is not None):
    custom_web_content[web_content.page] = web_content.content
session.close()

has_decks = num_decks > 0

errors.init(app)

modules = config['web'].get('modules', '').split()

bot_commands_list = []

from flask import make_response
from functools import wraps, update_wrapper

def nocache(view):
    @wraps(view)
    def no_cache(*args, **kwargs):
        response = make_response(view(*args, **kwargs))
        response.headers['Last-Modified'] = datetime.datetime.now()
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '-1'
        return response

    return update_wrapper(no_cache, view)


def add_to_command_list(command, alias):
    if command in bot_commands_list:
        return

    command.json_description = None

    try:
        if command.description is not None:
            command.json_description = json.loads(command.description)
            if 'description' in command.json_description:
                command.description = Markup(markdown.markdown(command.json_description['description']))
            if command.json_description.get('hidden', False) is True:
                return
    except ValueError:
        # Command description was not valid json
        pass
    except:
        log.info(command.json_description)
        log.exception('Unhandled exception BabyRage')
        return

    if command.command is None:
        command.command = alias
    if command.action is not None and command.action.type == 'multi':
        if command.command is not None:
            command.main_alias = command.command.split('|')[0]
        for inner_alias, inner_command in command.action.commands.items():
            add_to_command_list(inner_command, alias if command.command is None else command.main_alias + ' ' + inner_alias)
    else:
        command.main_alias = '!' + command.command.split('|')[0]
        if command.description is None:
            # Try to automatically figure out a description for the command
            if command.action is not None:
                if command.action.type == 'message':
                    command.description = command.action.response
                    if len(command.action.response) == 0:
                        return

        bot_commands_list.append(command)

@cron.scheduled_job('interval', minutes=2)
@time_nonclass_method
def update_commands():
    global bot_commands_list
    from tyggbot.models.command import CommandManager
    """
    with CommandManager().reload() as bot_commands:
        bot_commands_list = []

        for alias, command in bot_commands.items():
            add_to_command_list(command, alias)

        bot_commands_list = sorted(bot_commands_list, key=lambda x: (x.id or -1, x.main_alias))
        """
    bot_commands = CommandManager(None).reload()
    bot_commands_list = []

    for alias, command in bot_commands.items():
        add_to_command_list(command, alias)

    bot_commands_list = sorted(bot_commands_list, key=lambda x: (x.id or -1, x.main_alias))
    del bot_commands

update_commands()

@app.route('/')
def index():
    custom_content = custom_web_content.get('home', '')
    try:
        custom_content = Markup(markdown.markdown(custom_content))
    except:
        log.exception('Unhandled exception in def index')
    return render_template('index.html',
            custom_content=custom_content)

@app.route('/commands/')
def commands():
    custom_commands = []
    point_commands = []
    moderator_commands = []

    for command in bot_commands_list:
        if command.level > 100 or command.mod_only:
            moderator_commands.append(command)
        elif command.cost > 0:
            point_commands.append(command)
        else:
            custom_commands.append(command)

    """
    for command in cursor:
        action = json.loads(command['action'])
        command['aliases'] = ['!' + s for s in command['command'].split('|')]
        for alias in command['aliases']:
            alias = '!' + alias
        if action['type'] in ['say', 'me', 'whisper']:
            if command['description'] is None or 'Added by' in command['description']:
                command['description'] = action['message']

        command['arguments'] = []

        try:
            if command['description'] is not None:
                description = json.loads(command['description'])
                if 'description' in description:
                    command['description'] = description['description']
                if 'usage' in description:
                    if description['usage'] == 'whisper':
                        for x in range(0, len(command['aliases'])):
                            alias = command['aliases'][x]
                            command['aliases'][x] = '/w {0} {1}'.format(config['bot']['full_name'], alias)
                        for alias in command['aliases']:
                            command['aliases']
                    command['description'] = description['description']
                if 'arguments' in description:
                    command['arguments'] = description['arguments']
                if 'hidden' in description:
                    if description['hidden'] is True:
                        continue
        except ValueError:
            # Command description was not valid json
            pass
        except:
            pass

        if command['description']:
            try:
                command['description'] = Markup(markdown.markdown(command['description']))
            except:
                log.exception('Unhandled exception in markdown shit')
            if command['level'] > 100:
                moderator_commands.append(command)
            elif command['cost'] > 0:
                point_commands.append(command)
            elif not command['description'].startswith('Added by'):
                custom_commands.append(command)
    cursor.close()
    sqlconn.commit()
    """
    try:
        return render_template('commands.html',
                custom_commands=sorted(custom_commands, key=lambda f: f.command),
                point_commands=sorted(point_commands, key=lambda a: (a.cost, a.command)),
                moderator_commands=sorted(moderator_commands, key=lambda c: (c.level if c.mod_only is False else 500, c.command)))
    except Exception:
        log.exception('Unhandled exception in commands() render_template')
        return 'abc'


@app.route('/decks/')
def decks():
    session = DBManager.create_session()
    decks = session.query(Deck).order_by(Deck.last_used.desc(), Deck.first_used.desc()).all()
    session.close()
    return render_template('decks.html',
            decks=decks)


@app.route('/user/<username>')
def user_profile(username):
    session = DBManager.create_session()
    user = session.query(User).filter_by(username=username).one_or_none()
    if user is None:
        return render_template('no_user.html'), 404

    rank = session.query(func.Count(User.id)).filter(User.points > user.points).one()
    rank = rank[0] + 1
    session.close()

    user.rank = rank

    if user:
        return render_template('user.html',
                user=user)
    else:
        return render_template('no_user.html'), 404


@app.route('/points')
def points():
    session = DBManager.create_session()
    top_30_users = []
    for user in session.query(User).order_by(User.points.desc())[:30]:
        top_30_users.append(user)
    session.close()
    return render_template('points.html',
            top_30_users=top_30_users)


@app.route('/debug')
def debug():
    return render_template('debug.html')


@app.route('/stats')
def stats():
    top_5_commands = sorted(bot_commands_list, key=lambda c: c.num_uses, reverse=True)[:5]

    if 'linefarming' in modules:
        session = DBManager.create_session()
        top_5_line_farmers = session.query(User).order_by(User.num_lines.desc())[:5]
        session.close()
    else:
        top_5_line_farmers = []

    return render_template('stats.html',
            top_5_commands=top_5_commands,
            top_5_line_farmers=top_5_line_farmers)


@app.route('/contact')
def contact():
    return render_template('contact.html')


@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/highlights/<date>/')
def highlight_list_date(date):
    # Make sure we were passed a valid date
    try:
        parsed_date = datetime.datetime.strptime(date, '%Y-%m-%d')
    except ValueError:
        # Invalid date
        return redirect('/highlights/', 303)
    session = DBManager.create_session()
    dates_with_highlights = []
    highlights = session.query(StreamChunkHighlight).filter(cast(StreamChunkHighlight.created_at, Date) == parsed_date).order_by(StreamChunkHighlight.created_at.desc()).all()
    for highlight in session.query(StreamChunkHighlight):
        dates_with_highlights.append(datetime.datetime(
            year=highlight.created_at.year,
            month=highlight.created_at.month,
            day=highlight.created_at.day))

    try:
        return render_template('highlights_date.html',
                highlights=highlights,
                date=parsed_date,
                dates_with_highlights=set(dates_with_highlights))
    finally:
        session.close()

@app.route('/highlights/<date>/<highlight_id>', defaults={'highlight_title': None})
@app.route('/highlights/<date>/<highlight_id>-<highlight_title>')
def highlight_id(date, highlight_id, highlight_title=None):
    session = DBManager.create_session()
    highlight = session.query(StreamChunkHighlight).filter_by(id=highlight_id).first()
    if highlight is None:
        session.close()
        return render_template('highlight_404.html'), 404
    else:
        stream_chunk = highlight.stream_chunk
        stream = stream_chunk.stream
        session.close()
    return render_template('highlight.html',
            highlight=highlight,
            stream_chunk=stream_chunk,
            stream=stream)

@app.route('/highlights/')
def highlights():
    session = DBManager.create_session()
    dates_with_highlights = []
    highlights = session.query(StreamChunkHighlight).order_by(StreamChunkHighlight.created_at.desc()).all()
    for highlight in highlights:
        dates_with_highlights.append(datetime.datetime(
            year=highlight.created_at.year,
            month=highlight.created_at.month,
            day=highlight.created_at.day))
    try:
        return render_template('highlights.html',
                highlights=highlights[:5],
                dates_with_highlights=set(dates_with_highlights))
    finally:
        session.close()


@app.route('/discord')
def discord():
    return render_template('discord.html')


@app.route('/clr/overlay/<widget_id>')
@nocache
def clr_overlay(widget_id):
    print(widget_id)
    if widget_id == config['web']['clr_widget_id'] or True:
        return render_template('clr/overlay.html',
                widget={})
    else:
        return render_template('errors/404.html'), 404

@app.template_filter()
def date_format(value, format='full'):
    if format == 'full':
        date_format = '%Y-%m-%d %H:%M:%S'

    return value.strftime(date_format)

@app.template_filter('strftime')
def time_strftime(value, format):
    return value.strftime(format)

@app.template_filter('unix_timestamp')
def time_unix_timestamp(value):
    return value.timestamp()

@app.template_filter()
def number_format(value, tsep=',', dsep='.'):
    s = str(value)
    cnt = 0
    numchars = dsep + '0123456789'
    ls = len(s)
    while cnt < ls and s[cnt] not in numchars:
        cnt += 1

    lhs = s[:cnt]
    s = s[cnt:]
    if not dsep:
        cnt = -1
    else:
        cnt = s.rfind(dsep)
    if cnt > 0:
        rhs = dsep + s[cnt + 1:]
        s = s[:cnt]
    else:
        rhs = ''

    splt = ''
    while s != '':
        splt = s[-3:] + tsep + splt
        s = s[:-3]

    return lhs + splt[:-1] + rhs


default_variables = {
        'bot': {
            'name': config['main']['nickname'],
            },
        'site': {
            'domain': config['web']['domain'],
            },
        'streamer': {
            'name': config['web']['streamer_name'],
            'full_name': config['main']['streamer']
            },
        'has_decks': has_decks,
        'modules': modules,
        'current_time': datetime.datetime.now()
        }


@app.context_processor
def inject_default_variables():
    return default_variables


def time_since(t1, t2, format='long'):
    time_diff = t1 - t2
    if format == 'long':
        num_dict = ['day', 'hour', 'minute', 'second']
    else:
        num_dict = ['d', 'h', 'm', 's']
    num = [math.trunc(time_diff / 86400),
           math.trunc(time_diff / 3600 % 24),
           math.trunc(time_diff / 60 % 60),
           round(time_diff % 60, 1)]

    i = 0
    j = 0
    time_arr = []
    while i < 2 and j < 4:
        if num[j] > 0:
            if format == 'long':
                time_arr.append('{0:g} {1}{2}'.format(num[j], num_dict[j], 's' if num[j] > 1 else ''))
            else:
                time_arr.append('{0}{1}'.format(num[j], num_dict[j]))
            i += 1
        j += 1

    if format == 'long':
        return ' and '.join(time_arr)
    else:
        return ''.join(time_arr)


@app.template_filter('time_ago')
def time_ago(t, format='long'):
    return time_since(datetime.datetime.now().timestamp(), t.timestamp(), format)

if __name__ == '__main__':
    app.run(debug=args.debug, host=args.host, port=args.port)

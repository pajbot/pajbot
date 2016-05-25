import datetime

from flask import redirect
from flask import render_template
from sqlalchemy import cast
from sqlalchemy import Date
from sqlalchemy.orm import joinedload

from pajbot.managers.db import DBManager
from pajbot.models.stream import StreamChunkHighlight


def init(app):
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
        highlights = session.query(StreamChunkHighlight).options(joinedload('*')).filter(cast(StreamChunkHighlight.created_at, Date) == parsed_date).order_by(StreamChunkHighlight.created_at.desc()).all()
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
        with DBManager.create_session_scope() as db_session:
            highlight = db_session.query(StreamChunkHighlight).options(joinedload('*')).filter_by(id=highlight_id).first()
            if highlight is None:
                return render_template('highlight_404.html'), 404
            else:
                stream_chunk = highlight.stream_chunk
                stream = stream_chunk.stream
            return render_template('highlight.html',
                    highlight=highlight,
                    stream_chunk=stream_chunk,
                    stream=stream)

    @app.route('/highlights/')
    def highlights():
        session = DBManager.create_session()
        dates_with_highlights = []
        highlights = session.query(StreamChunkHighlight).options(joinedload('*')).filter(StreamChunkHighlight.created_at >= (datetime.datetime.utcnow() - datetime.timedelta(days=60))).order_by(StreamChunkHighlight.created_at_with_offset.desc()).all()
        for highlight in highlights:
            dates_with_highlights.append(datetime.datetime(
                year=highlight.created_at.year,
                month=highlight.created_at.month,
                day=highlight.created_at.day))
        try:
            return render_template('highlights.html',
                    highlights=highlights[:10],
                    dates_with_highlights=set(dates_with_highlights))
        finally:
            session.close()

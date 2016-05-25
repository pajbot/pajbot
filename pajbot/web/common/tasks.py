import logging

from pajbot.managers.db import DBManager
from pajbot.models.stream import StreamChunkHighlight

log = logging.getLogger(__name__)


def init(app):
    try:
        from uwsgidecorators import thread, timer

        @thread
        @timer(60)
        def get_highlight_thumbnails(no_clue_what_this_does):
            from pajbot.web.models.thumbnail import StreamThumbnailWriter
            with DBManager.create_session_scope() as db_session:
                highlights = db_session.query(StreamChunkHighlight).filter_by(thumbnail=None).all()
                if len(highlights) > 0:
                    log.info('Writing {} thumbnails...'.format(len(highlights)))
                    StreamThumbnailWriter(app.bot_config['main']['streamer'], [h.id for h in highlights])
                    log.info('Done!')
                    for highlight in highlights:
                        highlight.thumbnail = True
    except ImportError:
        log.exception('Import error, disregard if debugging.')
        pass

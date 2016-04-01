import logging

from pajbot.managers import DBManager
from pajbot.models.module import ModuleManager
from pajbot.models.stream import StreamChunkHighlight

log = logging.getLogger(__name__)


def init(app):
    def update_commands(signal_id):
        log.debug('Updating commands...')
        from pajbot.models.command import CommandManager
        bot_commands = CommandManager(
                socket_manager=None,
                module_manager=ModuleManager(None).load(),
                bot=None).load(load_examples=True)
        app.bot_commands_list = bot_commands.parse_for_web()

        app.bot_commands_list.sort(key=lambda x: (x.id or -1, x.main_alias))
        del bot_commands

    update_commands(26)
    try:
        import uwsgi
        from uwsgidecorators import thread, timer
        uwsgi.register_signal(26, 'worker', update_commands)
        uwsgi.add_timer(26, 60 * 10)

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
    pass

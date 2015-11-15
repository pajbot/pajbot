import logging

from flask import render_template

log = logging.getLogger(__name__)


def init(app):
    @app.errorhandler(404)
    def page_not_found(e):
        return render_template('errors/404.html'), 404

    @app.errorhandler(500)
    def internal_server_rrors(e):
        return render_template('errors/500.html'), 500

    @app.errorhandler(Exception)
    def all_exception_handler(error):
        log.exception('Unhandled exception')
        return render_template('errors/500.html'), 500

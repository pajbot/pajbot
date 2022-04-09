import logging

from flask import jsonify, render_template, request

log = logging.getLogger(__name__)


def init(app, config):
    @app.errorhandler(404)
    def page_not_found(e):
        if request.path.startswith("/api/"):
            return jsonify({"error": "No API endpoint here!"}), 404
        return render_template("errors/404.html"), 404

    @app.errorhandler(500)
    def internal_server_errors(e):
        if request.path.startswith("/api/"):
            return jsonify({"error": "Internal server error"}), 500
        return render_template("errors/500.html"), 500

    @app.errorhandler(403)
    def forbidden(e):
        if request.path.startswith("/api/"):
            return jsonify({"error": "Method not allowed"}), 403
        return render_template("errors/403.html"), 403

    @app.errorhandler(405)
    def method_not_allowed(e):
        if request.path.startswith("/api/"):
            return jsonify({"error": "Method not allowed"}), 405
        return render_template("errors/405_method_not_allowed.html"), 405

    @app.errorhandler(Exception)
    def all_exception_handler(error):
        log.exception("Unhandled exception")
        if request.path.startswith("/api/"):
            return jsonify({"error": "Internal server error - Unhandled exception"}), 500
        return render_template("errors/500_unhandled.html"), 500

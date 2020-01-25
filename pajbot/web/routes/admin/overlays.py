import logging

from flask import redirect
from flask import render_template
from flask import request
from flask import abort

from pajbot.web.utils import requires_level
from pajbot.managers.db import DBManager
from pajbot.models.web_sockets import WebSocket, Widget

log = logging.getLogger(__name__)

def init(page):
    @page.route("/overlays")
    @requires_level(500)
    def admin_overlays(**options):
        with DBManager.create_session_scope() as db_session:
            overlays = [x.jsonify() for x in WebSocket._all(db_session)]
        return render_template("admin/overlays.html", overlays=overlays)

    @page.route("/overlays/edit/<overlay_id>")
    @requires_level(500)
    def admin_overlays_edit(overlay_id, **options):
        with DBManager.create_session_scope() as db_session:
            log.info(overlay_id)
            try:
                WebSocket._by_id(db_session, int(overlay_id))._new_salt(db_session)
            except:
                return render_template("admin/no_overlay.html")
        return redirect("/admin/overlays")

    @page.route("/overlays/create", methods=['GET', 'POST'])
    @requires_level(500)
    def admin_overlays_create(**options):
        if request.method == "POST":
            log.info("POSTED!")
            try:
                widget_id = request.form["widget"].strip().lower()
            except (KeyError, ValueError):
                abort(403)
                return

            with DBManager.create_session_scope() as db_session:
                try:
                    if not Widget._by_id(db_session, int(widget_id)):
                        abort(403)
                        return
                except Exception as e:
                    log.info(e)
                    abort(403)
                    return
                WebSocket._create(db_session, int(widget_id))
                return redirect("/admin/overlays")
        else:
            with DBManager.create_session_scope() as db_session:
                widgets = [x.jsonify() for x in Widget._all(db_session)]
            return render_template("admin/create_overlay.html", widgets=widgets)

    @page.route("/overlays/remove/<overlay_id>")
    @requires_level(500)
    def admin_overlays_delete(overlay_id, **options):
        with DBManager.create_session_scope() as db_session:
            try:
                WebSocket._by_id(db_session, int(overlay_id))._remove(db_session)
            except:
                return render_template("admin/no_overlay.html")
        return redirect("/admin/overlays")

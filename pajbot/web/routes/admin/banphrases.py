from __future__ import annotations

from typing import Optional

import logging

from pajbot.managers.adminlog import AdminLogManager
from pajbot.managers.db import DBManager
from pajbot.models.banphrase import Banphrase, BanphraseData
from pajbot.models.sock import SocketClientManager
from pajbot.web.utils import requires_level

from flask import abort, redirect, render_template, request, session
from flask.typing import ResponseReturnValue
from sqlalchemy.orm import joinedload

log = logging.getLogger(__name__)


def init(page) -> None:
    @page.route("/banphrases/")
    @requires_level(500)
    def banphrases(**options) -> ResponseReturnValue:
        with DBManager.create_session_scope() as db_session:
            banphrases = (
                db_session.query(Banphrase)
                .options(
                    joinedload(Banphrase.data).joinedload(BanphraseData.user),
                    joinedload(Banphrase.data).joinedload(BanphraseData.user2),
                )
                .order_by(Banphrase.id)
                .all()
            )
            return render_template("admin/banphrases.html", banphrases=banphrases)

    @page.route("/banphrases/create", methods=["GET", "POST"])
    @requires_level(500)
    def banphrases_create(**options) -> ResponseReturnValue:
        session.pop("banphrase_created_id", None)
        session.pop("banphrase_edited_id", None)
        if request.method == "POST":
            id: Optional[int] = None
            try:
                if "id" in request.form:
                    id = int(request.form["id"])
                name = request.form["name"].strip()
                permanent = request.form.get("permanent", "off") == "on"
                warning = request.form.get("warning", "off") == "on"
                notify = request.form.get("notify", "off") == "on"
                case_sensitive = request.form.get("case_sensitive", "off") == "on"
                sub_immunity = request.form.get("sub_immunity", "off") == "on"
                remove_accents = request.form.get("remove_accents", "off") == "on"
                length = int(request.form["length"])
                phrase = request.form["phrase"]
                operator = request.form["operator"].strip().lower()
            except (KeyError, ValueError):
                abort(403)

            if not name:
                abort(403)

            if not phrase:
                abort(403)

            if length < 0 or length > 1209600:
                abort(403)

            valid_operators = ["contains", "startswith", "endswith", "exact", "regex"]
            if operator not in valid_operators:
                abort(403)

            user = options.get("user", None)

            if user is None:
                abort(403)

            options = {
                "name": name,
                "phrase": phrase,
                "permanent": permanent,
                "warning": warning,
                "notify": notify,
                "case_sensitive": case_sensitive,
                "sub_immunity": sub_immunity,
                "remove_accents": remove_accents,
                "length": length,
                "added_by": user.id,
                "edited_by": user.id,
                "operator": operator,
            }

            if id is None:
                banphrase = Banphrase(**options)
                banphrase.data = BanphraseData(banphrase.id, added_by=options["added_by"])

            with DBManager.create_session_scope(expire_on_commit=False) as db_session:
                if id is not None:
                    banphrase = (
                        db_session.query(Banphrase).options(joinedload(Banphrase.data)).filter_by(id=id).one_or_none()
                    )
                    if banphrase is None:
                        return redirect("/admin/banphrases/", 303)
                    banphrase.set(**options)
                    banphrase.data.set(edited_by=options["edited_by"])
                    log.info(f"Updated banphrase ID {banphrase.id} by user ID {options['edited_by']}")
                    AdminLogManager.post("Banphrase edited", user, banphrase.id, banphrase.phrase)
                else:
                    db_session.add(banphrase)
                    db_session.add(banphrase.data)
                    db_session.flush()
                    log.info(f"Added a new banphrase by user ID {options['added_by']}")
                    AdminLogManager.post("Banphrase added", user, banphrase.id, banphrase.phrase)

            SocketClientManager.send("banphrase.update", {"id": banphrase.id})
            if id is None:
                session["banphrase_created_id"] = banphrase.id
            else:
                session["banphrase_edited_id"] = banphrase.id
            return redirect("/admin/banphrases/", 303)
        else:
            return render_template("admin/create_banphrase.html")

    @page.route("/banphrases/edit/<banphrase_id>")
    @requires_level(500)
    def banphrases_edit(banphrase_id, **options) -> ResponseReturnValue:
        with DBManager.create_session_scope() as db_session:
            banphrase = db_session.query(Banphrase).filter_by(id=banphrase_id).one_or_none()

            if banphrase is None:
                return render_template("admin/banphrase_404.html"), 404

            return render_template("admin/create_banphrase.html", banphrase=banphrase)

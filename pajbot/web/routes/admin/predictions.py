from pajbot.managers.db import DBManager
from pajbot.modules.predict import PredictionRun, PredictionRunEntry
from pajbot.web.utils import requires_level

from flask import abort, render_template
from flask.typing import ResponseReturnValue
from sqlalchemy.orm import joinedload


def init(page) -> None:
    @page.route("/predictions/")
    @requires_level(500)
    def predictions(**options) -> ResponseReturnValue:
        with DBManager.create_session_scope() as db_session:
            predictions = db_session.query(PredictionRun).order_by(PredictionRun.started.desc()).all()

            for prediction in predictions:
                prediction.num_entries = (
                    db_session.query(PredictionRunEntry).filter_by(prediction_run_id=prediction.id).count()
                )
                pass

            return render_template("admin/predictions.html", predictions=predictions)

    @page.route("/predictions/view/<prediction_run_id>")
    @requires_level(500)
    def predictions_view(prediction_run_id, **options) -> ResponseReturnValue:
        with DBManager.create_session_scope() as db_session:
            prediction = db_session.query(PredictionRun).filter_by(id=prediction_run_id).one_or_none()
            if prediction is None:
                abort(404)

            entries = (
                db_session.query(PredictionRunEntry)
                .options(joinedload(PredictionRunEntry.user))
                .filter_by(prediction_run_id=prediction_run_id)
                .order_by(PredictionRunEntry.prediction.asc())
                .all()
            )
            prediction.num_entries = len(entries)

            return render_template("admin/predictions_view.html", prediction=prediction, entries=entries)

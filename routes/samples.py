from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required

from models import db, Sample
from parsers.lab_report import MATRIX_OPTIONS
from routes.projects import _parse_date

samples_bp = Blueprint("samples", __name__)


@samples_bp.route("/samples/<int:sample_id>", methods=["GET"])
@login_required
def detail(sample_id):
    sample = Sample.query.get_or_404(sample_id)
    results = sorted(sample.results, key=lambda r: (r.analyte or "").lower())
    return render_template(
        "samples/detail.html",
        sample=sample,
        project=sample.project,
        results=results,
    )


@samples_bp.route("/samples/<int:sample_id>/edit", methods=["GET"])
@login_required
def edit(sample_id):
    sample = Sample.query.get_or_404(sample_id)
    form = _form_from_sample(sample)
    return render_template(
        "samples/edit.html",
        sample=sample,
        form=form,
        matrix_options=MATRIX_OPTIONS,
    )


@samples_bp.route("/samples/<int:sample_id>/edit", methods=["POST"])
@login_required
def edit_save(sample_id):
    sample = Sample.query.get_or_404(sample_id)
    form = {
        "client_sample_id": (request.form.get("client_sample_id") or "").strip(),
        "lab_sample_id": (request.form.get("lab_sample_id") or "").strip(),
        "lab_workorder": (request.form.get("lab_workorder") or "").strip(),
        "matrix": (request.form.get("matrix") or "").strip(),
        "collection_date": (request.form.get("collection_date") or "").strip(),
        "collection_time": (request.form.get("collection_time") or "").strip(),
        "collection_end_time": (request.form.get("collection_end_time") or "").strip(),
        "sample_volume": (request.form.get("sample_volume") or "").strip(),
        "pump_flow_rate": (request.form.get("pump_flow_rate") or "").strip(),
        "employee_name": (request.form.get("employee_name") or "").strip(),
        "work_area": (request.form.get("work_area") or "").strip(),
        "task_description": (request.form.get("task_description") or "").strip(),
        "wind_speed": (request.form.get("wind_speed") or "").strip(),
        "wind_direction": (request.form.get("wind_direction") or "").strip(),
        "weather_conditions": (request.form.get("weather_conditions") or "").strip(),
        "weather_temperature": (request.form.get("weather_temperature") or "").strip(),
        "notes": (request.form.get("notes") or "").strip(),
    }

    if not form["client_sample_id"]:
        flash("Client Sample ID is required.", "error")
        return render_template("samples/edit.html", sample=sample, form=form, matrix_options=MATRIX_OPTIONS), 400
    if not form["matrix"]:
        flash("Matrix is required.", "error")
        return render_template("samples/edit.html", sample=sample, form=form, matrix_options=MATRIX_OPTIONS), 400
    if form["matrix"] not in MATRIX_OPTIONS:
        flash(f"Matrix must be one of: {', '.join(MATRIX_OPTIONS)}.", "error")
        return render_template("samples/edit.html", sample=sample, form=form, matrix_options=MATRIX_OPTIONS), 400

    collection_date = _parse_date(form["collection_date"]) if form["collection_date"] else None
    if form["collection_date"] and collection_date is None:
        flash("Collection date could not be parsed. Use YYYY-MM-DD or MM/DD/YYYY.", "error")
        return render_template("samples/edit.html", sample=sample, form=form, matrix_options=MATRIX_OPTIONS), 400

    sample.client_sample_id = form["client_sample_id"]
    sample.lab_sample_id = form["lab_sample_id"] or None
    sample.lab_workorder = form["lab_workorder"] or None
    sample.matrix = form["matrix"]
    sample.collection_date = collection_date
    sample.collection_time = form["collection_time"] or None
    sample.collection_end_time = form["collection_end_time"] or None
    sample.sample_volume = form["sample_volume"] or None
    sample.pump_flow_rate = form["pump_flow_rate"] or None
    sample.employee_name = form["employee_name"] or None
    sample.work_area = form["work_area"] or None
    sample.task_description = form["task_description"] or None
    sample.wind_speed = form["wind_speed"] or None
    sample.wind_direction = form["wind_direction"] or None
    sample.weather_conditions = form["weather_conditions"] or None
    sample.weather_temperature = form["weather_temperature"] or None
    sample.notes = form["notes"] or None

    db.session.commit()
    flash("Sample updated.", "success")
    return redirect(url_for("samples.detail", sample_id=sample.id))


def _form_from_sample(sample):
    return {
        "client_sample_id": sample.client_sample_id or "",
        "lab_sample_id": sample.lab_sample_id or "",
        "lab_workorder": sample.lab_workorder or "",
        "matrix": sample.matrix or "",
        "collection_date": sample.collection_date.strftime("%Y-%m-%d") if sample.collection_date else "",
        "collection_time": sample.collection_time or "",
        "collection_end_time": sample.collection_end_time or "",
        "sample_volume": sample.sample_volume or "",
        "pump_flow_rate": sample.pump_flow_rate or "",
        "employee_name": sample.employee_name or "",
        "work_area": sample.work_area or "",
        "task_description": sample.task_description or "",
        "wind_speed": sample.wind_speed or "",
        "wind_direction": sample.wind_direction or "",
        "weather_conditions": sample.weather_conditions or "",
        "weather_temperature": sample.weather_temperature or "",
        "notes": sample.notes or "",
    }

from datetime import datetime

from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required
from sqlalchemy import or_

from models import db, Project, Sample
from parsers.lab_report import MATRIX_OPTIONS
from routes._helpers import csv_response
from routes.projects import _parse_date
from utils.calculations import evaluate_result, worst_sample_status

samples_bp = Blueprint("samples", __name__)


AVAILABLE_STATUSES = [
    ("exceeded", "Exceeded"),
    ("warning", "Warning"),
    ("ok", "OK"),
    ("no_data", "No Data"),
]

NEUTRAL_STATUSES = ("no_thresholds", "no_value", "no_results")


def _parse_filter_args():
    """Parse filter query params from request.args and coerce/validate them.

    Returns (project_id, matrix, status_filter, q_str).
    """
    project_id_raw = (request.args.get("project_id") or "").strip()
    project_id = None
    if project_id_raw:
        try:
            project_id = int(project_id_raw)
        except ValueError:
            project_id = None

    matrix = (request.args.get("matrix") or "").strip()
    if matrix and matrix not in MATRIX_OPTIONS:
        matrix = ""

    status_filter = (request.args.get("status") or "").strip()
    valid_status_values = {key for key, _label in AVAILABLE_STATUSES}
    if status_filter and status_filter not in valid_status_values:
        status_filter = ""

    q_str = (request.args.get("q") or "").strip()
    return project_id, matrix, status_filter, q_str


def _filtered_samples(project_id, matrix, status_filter, q_str):
    """Apply parsed filters and return (samples_list, sample_statuses_dict).

    Performance note: worst_sample_status performs an N+1 query (one Results
    iteration per sample + one Threshold query per result). For the current
    dataset size this is fine. Optimize later by caching worst status on
    Sample or computing it in a background job.
    """
    query = Sample.query
    if project_id is not None:
        query = query.filter(Sample.project_id == project_id)
    if matrix:
        query = query.filter(Sample.matrix == matrix)
    if q_str:
        pattern = f"%{q_str}%"
        query = query.join(Project).filter(or_(
            Sample.client_sample_id.ilike(pattern),
            Sample.lab_workorder.ilike(pattern),
            Project.project_number.ilike(pattern),
        ))

    query = query.order_by(
        Sample.collection_date.desc(),
        Sample.client_sample_id.asc(),
    )
    all_samples = query.all()

    sample_statuses = {s.id: worst_sample_status(s) for s in all_samples}

    if status_filter:
        if status_filter == "no_data":
            all_samples = [
                s for s in all_samples
                if sample_statuses[s.id] in NEUTRAL_STATUSES
            ]
        else:
            all_samples = [
                s for s in all_samples
                if sample_statuses[s.id] == status_filter
            ]

    return all_samples, sample_statuses


@samples_bp.route("/samples", methods=["GET"])
@login_required
def list_samples():
    project_id, matrix, status_filter, q_str = _parse_filter_args()
    all_samples, sample_statuses = _filtered_samples(project_id, matrix, status_filter, q_str)

    filters = {
        "project_id": project_id,
        "matrix": matrix,
        "status": status_filter,
        "q": q_str,
    }
    filters_applied = bool(
        project_id is not None or matrix or status_filter or q_str
    )

    return render_template(
        "samples/list.html",
        samples=all_samples,
        sample_statuses=sample_statuses,
        filters=filters,
        filters_applied=filters_applied,
        available_projects=Project.query.order_by(Project.project_number).all(),
        available_matrices=MATRIX_OPTIONS,
        available_statuses=AVAILABLE_STATUSES,
        total_count=len(all_samples),
    )


@samples_bp.route("/samples/export", methods=["GET"])
@login_required
def export_samples():
    project_id, matrix, status_filter, q_str = _parse_filter_args()
    all_samples, _ = _filtered_samples(project_id, matrix, status_filter, q_str)

    timestamp = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
    filename = f"sampletrack_export_{timestamp}.csv"
    return csv_response(all_samples, filename)


@samples_bp.route("/samples/<int:sample_id>", methods=["GET"])
@login_required
def detail(sample_id):
    sample = Sample.query.get_or_404(sample_id)
    results = sorted(sample.results, key=lambda r: (r.analyte or "").lower())
    result_evaluations = {r.id: evaluate_result(sample, r) for r in results}
    return render_template(
        "samples/detail.html",
        sample=sample,
        project=sample.project,
        results=results,
        result_evaluations=result_evaluations,
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
        "collection_start_time": (request.form.get("collection_start_time") or "").strip(),
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
    sample.collection_start_time = form["collection_start_time"] or None
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
        "collection_start_time": sample.collection_start_time or "",
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

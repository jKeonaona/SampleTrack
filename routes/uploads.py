import json
import os
import tempfile

from flask import Blueprint, render_template, request, redirect, url_for, flash

from models import db, Project, Sample, Result
from parsers.lab_report import MATRIX_OPTIONS, parse_lab_report
from routes.projects import _parse_date, _parse_datetime, _parse_numeric

uploads_bp = Blueprint("uploads", __name__, url_prefix="/upload")


@uploads_bp.route("/", methods=["GET"])
def dump():
    return render_template("uploads/dump.html")


@uploads_bp.route("/", methods=["POST"])
def upload():
    uploaded = request.files.get("report_pdf")
    if uploaded is None or not uploaded.filename:
        flash("Please choose a PDF to upload.", "error")
        return redirect(url_for("uploads.dump"))
    if not uploaded.filename.lower().endswith(".pdf"):
        flash("Only PDF files are accepted.", "error")
        return redirect(url_for("uploads.dump"))

    tmp_fd, tmp_path = tempfile.mkstemp(suffix=".pdf")
    os.close(tmp_fd)
    try:
        uploaded.save(tmp_path)
        parser_data = parse_lab_report(tmp_path)
    finally:
        try:
            os.remove(tmp_path)
        except OSError:
            pass

    project_number = parser_data.get("project_number")
    existing_project = None
    if project_number:
        existing_project = Project.query.filter_by(project_number=project_number).first()

    parser_data_json = json.dumps(parser_data)
    return render_template(
        "uploads/dump_confirm.html",
        parser_data=parser_data,
        parser_data_json=parser_data_json,
        matrix_options=MATRIX_OPTIONS,
        existing_project=existing_project,
        project_exists=existing_project is not None,
    )


@uploads_bp.route("/save", methods=["POST"])
def save():
    raw = request.form.get("parser_data") or ""
    try:
        parser_data = json.loads(raw)
    except json.JSONDecodeError:
        flash("Could not read parsed data. Please re-upload the PDF.", "error")
        return redirect(url_for("uploads.dump"))

    project_number = (parser_data.get("project_number") or "").strip()
    if not project_number:
        flash(
            "No project number detected in the PDF. "
            "Open the project, then upload the report from its detail page.",
            "error",
        )
        return redirect(url_for("uploads.dump"))

    project_name = (parser_data.get("project_name") or "").strip()
    project = Project.query.filter_by(project_number=project_number).first()
    if project is None:
        project = Project(
            project_number=project_number,
            name=project_name or "Unnamed Project",
            status="active",
        )
        db.session.add(project)
        db.session.flush()
        flash(f"Auto-created new project {project_number}: {project.name}", "success")

    workorder = parser_data.get("workorder")
    samples_in = parser_data.get("samples") or []

    sample_count = 0
    result_count = 0
    for idx, sample_data in enumerate(samples_in):
        matrix = (request.form.get(f"matrix_{idx}") or sample_data.get("matrix") or "Other").strip()

        sample = Sample(
            project_id=project.id,
            client_sample_id=(sample_data.get("client_sample_id") or sample_data.get("lab_sample_id") or "UNKNOWN"),
            lab_sample_id=sample_data.get("lab_sample_id"),
            lab_workorder=workorder,
            matrix=matrix,
            collection_date=_parse_date(sample_data.get("collection_date")),
            collection_time=sample_data.get("collection_time"),
            sample_volume=sample_data.get("sample_volume"),
        )
        db.session.add(sample)
        db.session.flush()
        sample_count += 1

        for r_data in sample_data.get("results") or []:
            analyte = (r_data.get("analyte") or "").strip()
            result_value = (r_data.get("result_value") or "").strip()
            if not analyte or not result_value:
                continue
            db.session.add(Result(
                sample_id=sample.id,
                analyte=analyte,
                result_value=result_value,
                result_numeric=_parse_numeric(result_value),
                result_units=r_data.get("result_units") or sample_data.get("units"),
                reporting_limit=r_data.get("reporting_limit"),
                dilution_factor=r_data.get("dilution_factor"),
                method_reference=sample_data.get("method"),
                lab_report_number=workorder,
                date_analyzed=_parse_datetime(r_data.get("date_analyzed")),
            ))
            result_count += 1

    db.session.commit()
    flash(
        f"Saved {sample_count} samples and {result_count} results to project {project_number}.",
        "success",
    )
    return redirect(url_for("projects.detail", project_id=project.id))

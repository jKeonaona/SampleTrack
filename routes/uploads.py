import json
import os
import tempfile

from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required

from models import db, Project, Sample, Result
from parsers.lab_report import MATRIX_OPTIONS, parse_lab_report
from routes.projects import _parse_date, _parse_datetime, _parse_numeric

uploads_bp = Blueprint("uploads", __name__, url_prefix="/upload")


def _parsed_sample_methods(sample_dict):
    methods = set()
    sample_method = sample_dict.get("method")
    if sample_method:
        methods.add(sample_method)
    for r in sample_dict.get("results") or []:
        if isinstance(r, dict):
            rm = r.get("method")
            if rm:
                methods.add(rm)
    return methods


def _existing_sample_methods(sample_obj):
    return {r.method_reference for r in sample_obj.results if r.method_reference}


@uploads_bp.route("/", methods=["GET"])
@login_required
def dump():
    return render_template("uploads/dump.html")


@uploads_bp.route("/", methods=["POST"])
@login_required
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

    workorder = parser_data.get("workorder")
    workorder_exists = False
    existing_workorder_samples = []
    if workorder:
        matches = (
            Sample.query
            .filter_by(lab_workorder=workorder)
            .limit(5)
            .all()
        )
        if matches:
            workorder_exists = True
            for m in matches:
                existing_workorder_samples.append({
                    "client_sample_id": m.client_sample_id,
                    "project_number": m.project.project_number if m.project else None,
                    "project_id": m.project_id,
                    "collection_date": m.collection_date.strftime("%Y-%m-%d") if m.collection_date else None,
                })

    samples = parser_data.get("samples") or []
    if existing_project is not None:
        for s in samples:
            csid = s.get("client_sample_id")
            if not csid:
                s["client_id_conflict"] = False
                continue

            parsed_methods = _parsed_sample_methods(s)
            existing_matches = Sample.query.filter_by(
                project_id=existing_project.id,
                client_sample_id=csid,
            ).all()

            conflict = None
            for existing in existing_matches:
                overlap = parsed_methods & _existing_sample_methods(existing)
                if overlap:
                    conflict = (existing, overlap)
                    break

            if conflict is not None:
                existing, overlap = conflict
                s["client_id_conflict"] = True
                s["existing_sample"] = {
                    "id": existing.id,
                    "lab_workorder": existing.lab_workorder,
                    "collection_date": existing.collection_date.strftime("%Y-%m-%d") if existing.collection_date else None,
                    "methods": sorted(overlap),
                }
            else:
                s["client_id_conflict"] = False
    else:
        for s in samples:
            s["client_id_conflict"] = False

    parser_data_json = json.dumps(parser_data)
    return render_template(
        "uploads/dump_confirm.html",
        parser_data=parser_data,
        parser_data_json=parser_data_json,
        matrix_options=MATRIX_OPTIONS,
        existing_project=existing_project,
        project_exists=existing_project is not None,
        workorder_exists=workorder_exists,
        existing_workorder_samples=existing_workorder_samples,
    )


@uploads_bp.route("/save", methods=["POST"])
@login_required
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

    saved_count = 0
    result_count = 0
    skipped_count = 0
    for idx, sample_data in enumerate(samples_in):
        matrix = (request.form.get(f"matrix_{idx}") or sample_data.get("matrix") or "Other").strip()
        client_sample_id = (sample_data.get("client_sample_id") or sample_data.get("lab_sample_id") or "UNKNOWN")
        save_anyway = request.form.get(f"save_anyway_{idx}") == "on"

        parsed_methods = _parsed_sample_methods(sample_data)
        existing_matches = Sample.query.filter_by(
            project_id=project.id,
            client_sample_id=client_sample_id,
        ).all()
        has_overlap = any(
            parsed_methods & _existing_sample_methods(existing)
            for existing in existing_matches
        )
        if has_overlap and not save_anyway:
            skipped_count += 1
            continue

        sample = Sample(
            project_id=project.id,
            client_sample_id=client_sample_id,
            lab_sample_id=sample_data.get("lab_sample_id"),
            lab_workorder=workorder,
            matrix=matrix,
            collection_date=_parse_date(sample_data.get("collection_date")),
            collection_time=sample_data.get("collection_time"),
            sample_volume=sample_data.get("sample_volume"),
        )
        db.session.add(sample)
        db.session.flush()
        saved_count += 1

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
    msg = f"Saved {saved_count} samples and {result_count} results to project {project_number}."
    if skipped_count > 0:
        msg += f" Skipped {skipped_count} duplicate sample(s)."
    flash(msg, "success")
    return redirect(url_for("projects.detail", project_id=project.id))

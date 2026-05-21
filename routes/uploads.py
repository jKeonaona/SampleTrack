import json
import os
import tempfile

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, session
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


def _process_uploaded_file(uploaded):
    """Process one uploaded file. Returns (kind, entry, auto_created_info).

    kind: "saved" or "failed".
    entry: dict matching saved_files or failed_files structure (no "status" field).
    auto_created_info: dict to append to auto_created_projects, or None.

    Performs db.session.flush() but does NOT commit. Caller is responsible for
    db.session.commit() (or rollback).
    """
    filename = uploaded.filename
    if not filename.lower().endswith(".pdf"):
        return "failed", {"filename": filename, "reason": "Not a PDF file."}, None

    tmp_fd, tmp_path = tempfile.mkstemp(suffix=".pdf")
    os.close(tmp_fd)
    try:
        uploaded.save(tmp_path)

        try:
            parser_data = parse_lab_report(tmp_path)
        except Exception as exc:
            return "failed", {
                "filename": filename,
                "reason": f"Parse error: {type(exc).__name__}: {exc}",
            }, None

        project_number = (parser_data.get("project_number") or "").strip()
        if not project_number:
            return "failed", {
                "filename": filename,
                "reason": "No project number detected in PDF.",
            }, None

        samples_in = parser_data.get("samples") or []
        if not samples_in:
            return "failed", {
                "filename": filename,
                "reason": "No samples extracted from PDF.",
            }, None

        project_name = (parser_data.get("project_name") or "").strip()
        project = Project.query.filter_by(project_number=project_number).first()
        was_auto_created = False
        auto_created_info = None
        if project is None:
            project = Project(
                project_number=project_number,
                name=project_name or "Unnamed Project",
                status="active",
            )
            db.session.add(project)
            db.session.flush()
            was_auto_created = True
            auto_created_info = {
                "id": project.id,
                "project_number": project.project_number,
                "name": project.name,
            }

        workorder = parser_data.get("workorder")
        file_samples_saved = 0
        file_results_saved = 0
        file_duplicates_skipped = 0

        for sample_data in samples_in:
            client_sample_id = (
                sample_data.get("client_sample_id")
                or sample_data.get("lab_sample_id")
                or "UNKNOWN"
            )

            parsed_methods = _parsed_sample_methods(sample_data)
            existing_matches = Sample.query.filter_by(
                project_id=project.id,
                client_sample_id=client_sample_id,
            ).all()
            has_overlap = any(
                parsed_methods & _existing_sample_methods(existing)
                for existing in existing_matches
            )
            if has_overlap:
                file_duplicates_skipped += 1
                continue

            matrix = (sample_data.get("matrix") or "Other").strip() or "Other"
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
            file_samples_saved += 1

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
                file_results_saved += 1

        entry = {
            "filename": filename,
            "project_number": project.project_number,
            "project_name": project.name,
            "project_id": project.id,
            "was_auto_created": was_auto_created,
            "samples_saved": file_samples_saved,
            "results_saved": file_results_saved,
            "duplicates_skipped": file_duplicates_skipped,
        }
        return "saved", entry, auto_created_info
    finally:
        try:
            os.remove(tmp_path)
        except OSError:
            pass


@uploads_bp.route("/", methods=["GET"])
@login_required
def dump():
    return render_template("uploads/dump.html")


@uploads_bp.route("/", methods=["POST"])
@login_required
def upload():
    files = [f for f in request.files.getlist("files") if f and f.filename]
    if not files:
        flash("Select at least one PDF to upload.", "error")
        return redirect(url_for("uploads.dump"))

    saved_files = []
    failed_files = []
    auto_created_projects = []
    total_samples_saved = 0
    total_results_saved = 0
    total_duplicates_skipped = 0

    for uploaded in files:
        kind, entry, auto_created_info = _process_uploaded_file(uploaded)
        if kind == "saved":
            saved_files.append(entry)
            total_samples_saved += entry["samples_saved"]
            total_results_saved += entry["results_saved"]
            total_duplicates_skipped += entry["duplicates_skipped"]
            if auto_created_info is not None:
                auto_created_projects.append(auto_created_info)
        else:
            failed_files.append(entry)

    db.session.commit()

    return render_template(
        "uploads/dump_summary.html",
        saved_files=saved_files,
        failed_files=failed_files,
        auto_created_projects=auto_created_projects,
        total_samples_saved=total_samples_saved,
        total_results_saved=total_results_saved,
        total_duplicates_skipped=total_duplicates_skipped,
    )


@uploads_bp.route("/start", methods=["POST"])
@login_required
def upload_start():
    session["bulk_upload_results"] = {
        "saved_files": [],
        "failed_files": [],
        "auto_created_projects": [],
        "totals": {
            "samples_saved": 0,
            "results_saved": 0,
            "duplicates_skipped": 0,
        },
    }
    session.modified = True
    return jsonify({"success": True})


def _empty_bulk_results():
    return {
        "saved_files": [],
        "failed_files": [],
        "auto_created_projects": [],
        "totals": {
            "samples_saved": 0,
            "results_saved": 0,
            "duplicates_skipped": 0,
        },
    }


@uploads_bp.route("/single", methods=["POST"])
@login_required
def upload_single():
    uploaded = request.files.get("file")
    if uploaded is None or not uploaded.filename:
        return jsonify({"success": False, "error": "No file provided"}), 400

    results = session.get("bulk_upload_results")
    if not isinstance(results, dict):
        results = _empty_bulk_results()

    try:
        kind, entry, auto_created_info = _process_uploaded_file(uploaded)
    except Exception as exc:
        db.session.rollback()
        kind = "failed"
        entry = {
            "filename": uploaded.filename,
            "reason": f"Save error: {type(exc).__name__}: {exc}",
        }
        auto_created_info = None

    if kind == "saved":
        results.setdefault("saved_files", []).append(entry)
        totals = results.setdefault("totals", {})
        totals["samples_saved"] = totals.get("samples_saved", 0) + entry["samples_saved"]
        totals["results_saved"] = totals.get("results_saved", 0) + entry["results_saved"]
        totals["duplicates_skipped"] = totals.get("duplicates_skipped", 0) + entry["duplicates_skipped"]
        if auto_created_info is not None:
            existing_ids = {p["id"] for p in results.setdefault("auto_created_projects", [])}
            if auto_created_info["id"] not in existing_ids:
                results["auto_created_projects"].append(auto_created_info)
        db.session.commit()
        outcome = {
            "filename": entry["filename"],
            "status": "saved",
            "project_number": entry["project_number"],
            "project_name": entry["project_name"],
            "was_auto_created": entry["was_auto_created"],
            "samples_saved": entry["samples_saved"],
            "duplicates_skipped": entry["duplicates_skipped"],
        }
    else:
        results.setdefault("failed_files", []).append(entry)
        db.session.rollback()
        outcome = {
            "filename": entry["filename"],
            "status": "failed",
            "reason": entry["reason"],
        }

    session["bulk_upload_results"] = results
    session.modified = True

    return jsonify({"success": True, "outcome": outcome})


@uploads_bp.route("/summary", methods=["GET"])
@login_required
def upload_summary():
    results = session.get("bulk_upload_results")
    if not isinstance(results, dict) or not (
        results.get("saved_files") or results.get("failed_files")
    ):
        flash("No upload batch found.", "error")
        return redirect(url_for("uploads.dump"))

    totals = results.get("totals") or {}
    return render_template(
        "uploads/dump_summary.html",
        saved_files=results.get("saved_files") or [],
        failed_files=results.get("failed_files") or [],
        auto_created_projects=results.get("auto_created_projects") or [],
        total_samples_saved=totals.get("samples_saved", 0),
        total_results_saved=totals.get("results_saved", 0),
        total_duplicates_skipped=totals.get("duplicates_skipped", 0),
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

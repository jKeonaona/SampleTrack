import json
import os
import tempfile
from datetime import date, datetime

from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required

from models import db, Project, Sample, Result
from parsers.lab_report import MATRIX_OPTIONS, parse_lab_report
from utils.calculations import project_status_summary, worst_sample_status

projects_bp = Blueprint("projects", __name__, url_prefix="/projects")


@projects_bp.route("/", methods=["GET"])
@login_required
def list_projects():
    projects = Project.query.order_by(Project.created_at.desc()).all()
    return render_template("projects/list.html", projects=projects)


@projects_bp.route("/new", methods=["GET"])
@login_required
def new():
    return render_template("projects/new.html", form={})


@projects_bp.route("/", methods=["POST"])
@login_required
def create():
    form = {
        "project_number": (request.form.get("project_number") or "").strip(),
        "name": (request.form.get("name") or "").strip(),
        "client": (request.form.get("client") or "").strip(),
        "location": (request.form.get("location") or "").strip(),
        "status": (request.form.get("status") or "active").strip(),
    }

    if not form["project_number"]:
        flash("Project number is required.", "error")
        return render_template("projects/new.html", form=form), 400
    if not form["name"]:
        flash("Name is required.", "error")
        return render_template("projects/new.html", form=form), 400

    existing = Project.query.filter_by(project_number=form["project_number"]).first()
    if existing is not None:
        flash(f"Project number '{form['project_number']}' already exists.", "error")
        return render_template("projects/new.html", form=form), 400

    project = Project(
        project_number=form["project_number"],
        name=form["name"],
        client=form["client"] or None,
        location=form["location"] or None,
        status=form["status"] or "active",
    )
    db.session.add(project)
    db.session.commit()

    flash(f"Project '{project.project_number}' created.", "success")
    return redirect(url_for("projects.detail", project_id=project.id))


@projects_bp.route("/<int:project_id>", methods=["GET"])
@login_required
def detail(project_id):
    project = Project.query.get_or_404(project_id)
    samples = (
        Sample.query
        .filter_by(project_id=project.id)
        .order_by(Sample.collection_date.desc(), Sample.client_sample_id.asc())
        .all()
    )
    sample_statuses = {s.id: worst_sample_status(s) for s in samples}
    project_summary = project_status_summary(samples)
    return render_template(
        "projects/detail.html",
        project=project,
        samples=samples,
        sample_statuses=sample_statuses,
        project_summary=project_summary,
    )


VALID_PROJECT_STATUSES = ("active", "archived", "complete")


@projects_bp.route("/<int:project_id>/edit", methods=["GET"])
@login_required
def edit(project_id):
    project = Project.query.get_or_404(project_id)
    form = {
        "project_number": project.project_number,
        "name": project.name or "",
        "client": project.client or "",
        "location": project.location or "",
        "status": project.status or "active",
    }
    return render_template("projects/edit.html", project=project, form=form)


@projects_bp.route("/<int:project_id>/edit", methods=["POST"])
@login_required
def edit_save(project_id):
    project = Project.query.get_or_404(project_id)
    form = {
        "project_number": (request.form.get("project_number") or "").strip(),
        "name": (request.form.get("name") or "").strip(),
        "client": (request.form.get("client") or "").strip(),
        "location": (request.form.get("location") or "").strip(),
        "status": (request.form.get("status") or "active").strip(),
    }

    if not form["project_number"]:
        flash("Project number is required.", "error")
        return render_template("projects/edit.html", project=project, form=form), 400

    if form["status"] not in VALID_PROJECT_STATUSES:
        flash(f"Status must be one of: {', '.join(VALID_PROJECT_STATUSES)}.", "error")
        return render_template("projects/edit.html", project=project, form=form), 400

    if form["project_number"] != project.project_number:
        clash = Project.query.filter_by(project_number=form["project_number"]).first()
        if clash is not None and clash.id != project.id:
            flash(f"Project number '{form['project_number']}' is already in use.", "error")
            return render_template("projects/edit.html", project=project, form=form), 400

    project.project_number = form["project_number"]
    project.name = form["name"] or "Unnamed Project"
    project.client = form["client"] or None
    project.location = form["location"] or None
    project.status = form["status"]
    db.session.commit()

    flash("Project updated.", "success")
    return redirect(url_for("projects.detail", project_id=project.id))


@projects_bp.route("/<int:project_id>/upload", methods=["GET"])
@login_required
def upload_new(project_id):
    project = Project.query.get_or_404(project_id)
    return render_template("uploads/new.html", project=project)


@projects_bp.route("/<int:project_id>/upload", methods=["POST"])
@login_required
def upload(project_id):
    project = Project.query.get_or_404(project_id)

    uploaded = request.files.get("report_pdf")
    if uploaded is None or not uploaded.filename:
        flash("Please choose a PDF to upload.", "error")
        return redirect(url_for("projects.upload_new", project_id=project.id))
    if not uploaded.filename.lower().endswith(".pdf"):
        flash("Only PDF files are accepted.", "error")
        return redirect(url_for("projects.upload_new", project_id=project.id))

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

    parser_data_json = json.dumps(parser_data)
    return render_template(
        "uploads/confirm.html",
        project=project,
        parser_data=parser_data,
        parser_data_json=parser_data_json,
        matrix_options=MATRIX_OPTIONS,
    )


@projects_bp.route("/<int:project_id>/upload/save", methods=["POST"])
@login_required
def upload_save(project_id):
    project = Project.query.get_or_404(project_id)

    raw = request.form.get("parser_data") or ""
    try:
        parser_data = json.loads(raw)
    except json.JSONDecodeError:
        flash("Could not read parsed data. Please re-upload the PDF.", "error")
        return redirect(url_for("projects.upload_new", project_id=project.id))

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
    flash(f"Saved {sample_count} samples and {result_count} results.", "success")
    return redirect(url_for("projects.detail", project_id=project.id))


def _parse_date(value):
    if not value:
        return None
    value = value.strip()
    for fmt in ("%m/%d/%Y", "%m/%d/%y", "%Y-%m-%d", "%m-%d-%Y"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    return None


def _parse_datetime(value):
    if not value:
        return None
    value = value.strip()
    for fmt in (
        "%m/%d/%Y %H:%M",
        "%m/%d/%Y %I:%M %p",
        "%m/%d/%Y",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%d",
    ):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    return None


def _parse_numeric(value):
    if value is None:
        return None
    cleaned = str(value).strip().replace(",", "")
    if cleaned == "" or cleaned.upper() == "ND":
        return None
    try:
        return float(cleaned)
    except ValueError:
        return None

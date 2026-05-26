from datetime import datetime

from flask import Blueprint, abort, flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from models import FieldSampleRecord, Project, Sample, db

fsr_bp = Blueprint("fsr", __name__, url_prefix="/fsr")


def _empty_form():
    return {
        "client_sample_id": "",
        "project_id": "",
        "job_number": "",
        "collection_date": "",
        "collection_time": "",
        "collected_by": "",
        "location_description": "",
        "matrix_specific_notes": "",
        "analytical_methods_requested": "",
        "laboratory_sent_to": "",
        "date_sent_to_lab": "",
        "general_notes": "",
    }


def _form_from_fsr(fsr):
    return {
        "client_sample_id": fsr.client_sample_id or "",
        "project_id": fsr.project_id or "",
        "job_number": fsr.job_number or "",
        "collection_date": fsr.collection_date or "",
        "collection_time": fsr.collection_time or "",
        "collected_by": fsr.collected_by or "",
        "location_description": fsr.location_description or "",
        "matrix_specific_notes": fsr.matrix_specific_notes or "",
        "analytical_methods_requested": fsr.analytical_methods_requested or "",
        "laboratory_sent_to": fsr.laboratory_sent_to or "",
        "date_sent_to_lab": fsr.date_sent_to_lab or "",
        "general_notes": fsr.general_notes or "",
    }


def _form_from_request():
    form = request.form
    return {
        "client_sample_id": (form.get("client_sample_id") or "").strip(),
        "project_id": (form.get("project_id") or "").strip(),
        "job_number": (form.get("job_number") or "").strip(),
        "collection_date": (form.get("collection_date") or "").strip(),
        "collection_time": (form.get("collection_time") or "").strip(),
        "collected_by": (form.get("collected_by") or "").strip(),
        "location_description": (form.get("location_description") or "").strip(),
        "matrix_specific_notes": (form.get("matrix_specific_notes") or "").strip(),
        "analytical_methods_requested": (form.get("analytical_methods_requested") or "").strip(),
        "laboratory_sent_to": (form.get("laboratory_sent_to") or "").strip(),
        "date_sent_to_lab": (form.get("date_sent_to_lab") or "").strip(),
        "general_notes": (form.get("general_notes") or "").strip(),
    }


def _apply_form_to_fsr(fsr, form):
    project_id_raw = form.get("project_id") or ""
    try:
        project_id = int(project_id_raw) if project_id_raw else None
    except ValueError:
        project_id = None

    fsr.client_sample_id = form["client_sample_id"]
    fsr.project_id = project_id
    fsr.job_number = form["job_number"] or None
    fsr.collection_date = form["collection_date"] or None
    fsr.collection_time = form["collection_time"] or None
    fsr.collected_by = form["collected_by"] or None
    fsr.location_description = form["location_description"] or None
    fsr.matrix_specific_notes = form["matrix_specific_notes"] or None
    fsr.analytical_methods_requested = form["analytical_methods_requested"] or None
    fsr.laboratory_sent_to = form["laboratory_sent_to"] or None
    fsr.date_sent_to_lab = form["date_sent_to_lab"] or None
    fsr.general_notes = form["general_notes"] or None


def _render_form(template, form, fsr=None):
    return render_template(
        template,
        form=form,
        fsr=fsr,
        available_projects=Project.query.order_by(Project.project_number).all(),
    )


@fsr_bp.route("", methods=["GET"])
@fsr_bp.route("/", methods=["GET"])
@login_required
def list_fsr():
    records = FieldSampleRecord.query.order_by(FieldSampleRecord.created_at.desc()).all()

    sample_ids = {r.client_sample_id for r in records if r.client_sample_id}
    linked = set()
    if sample_ids:
        rows = (
            db.session.query(Sample.client_sample_id)
            .filter(Sample.client_sample_id.in_(sample_ids))
            .distinct()
            .all()
        )
        linked = {row[0] for row in rows}

    return render_template(
        "fsr/list.html",
        records=records,
        linked_sample_ids=linked,
    )


@fsr_bp.route("/new", methods=["GET"])
@login_required
def new():
    form = _empty_form()
    prefill = (request.args.get("client_sample_id") or "").strip()
    if prefill:
        form["client_sample_id"] = prefill
    return _render_form("fsr/new.html", form)


@fsr_bp.route("/new", methods=["POST"])
@login_required
def create():
    form = _form_from_request()
    if not form["client_sample_id"]:
        flash("Client Sample ID is required.", "error")
        return _render_form("fsr/new.html", form), 400

    fsr = FieldSampleRecord(created_by_user_id=current_user.id)
    _apply_form_to_fsr(fsr, form)
    db.session.add(fsr)
    db.session.commit()
    flash("Field Sample Record created.", "success")
    return redirect(url_for("fsr.detail", id=fsr.id))


@fsr_bp.route("/<int:id>", methods=["GET"])
@login_required
def detail(id):
    fsr = FieldSampleRecord.query.get_or_404(id)
    linked_sample = Sample.query.filter_by(client_sample_id=fsr.client_sample_id).first()
    return render_template(
        "fsr/detail.html",
        fsr=fsr,
        linked_sample=linked_sample,
    )


@fsr_bp.route("/<int:id>/edit", methods=["GET"])
@login_required
def edit(id):
    fsr = FieldSampleRecord.query.get_or_404(id)
    form = _form_from_fsr(fsr)
    return _render_form("fsr/edit.html", form, fsr=fsr)


@fsr_bp.route("/<int:id>/edit_save", methods=["POST"])
@login_required
def edit_save(id):
    is_ajax = (
        request.headers.get("X-Requested-With") == "XMLHttpRequest"
        or request.is_json
    )
    fsr = FieldSampleRecord.query.get_or_404(id)
    form = _form_from_request()
    if not form["client_sample_id"]:
        if is_ajax:
            return jsonify({"status": "error", "message": "Client Sample ID is required."}), 400
        flash("Client Sample ID is required.", "error")
        return _render_form("fsr/edit.html", form, fsr=fsr), 400

    _apply_form_to_fsr(fsr, form)
    db.session.commit()

    if is_ajax:
        return jsonify({
            "status": "ok",
            "saved_at": datetime.utcnow().isoformat(),
        })

    flash("Field Sample Record updated.", "success")
    return redirect(url_for("fsr.detail", id=fsr.id))


@fsr_bp.route("/<int:id>/delete", methods=["POST"])
@login_required
def delete(id):
    if getattr(current_user, "role", None) != "admin":
        abort(403)
    fsr = FieldSampleRecord.query.get_or_404(id)
    db.session.delete(fsr)
    db.session.commit()
    flash("Field Sample Record deleted.", "success")
    return redirect(url_for("fsr.list_fsr"))

from datetime import datetime

from flask import Blueprint, flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from models import AirMonitorReport, Project, Sample, SamplingEvent, db
from utils.sample_id import (
    MATRIX_CODE_OPTIONS,
    generate_sample_id,
    matrix_from_code,
    next_sequence_number,
)

events_bp = Blueprint("events", __name__, url_prefix="/events")


PHASE_OPTIONS = ("Before", "During", "After")
AM_PM_OPTIONS = ("AM", "PM")
TEMP_UNIT_OPTIONS = ("F", "C")


@events_bp.route("", methods=["GET"])
@events_bp.route("/", methods=["GET"])
@login_required
def list_events():
    events = (
        SamplingEvent.query
        .order_by(SamplingEvent.event_date.desc().nullslast(), SamplingEvent.created_at.desc())
        .all()
    )

    event_ids = [e.id for e in events]
    sample_id_to_event = {}
    samples_by_event = {eid: [] for eid in event_ids}
    if event_ids:
        rows = Sample.query.filter(Sample.sampling_event_id.in_(event_ids)).all()
        for s in rows:
            samples_by_event[s.sampling_event_id].append(s)
            sample_id_to_event[s.client_sample_id] = s.sampling_event_id

    amr_counts = {eid: 0 for eid in event_ids}
    if sample_id_to_event:
        amrs = AirMonitorReport.query.filter(
            AirMonitorReport.client_sample_id.in_(sample_id_to_event.keys())
        ).all()
        for amr in amrs:
            eid = sample_id_to_event.get(amr.client_sample_id)
            if eid is not None:
                amr_counts[eid] = amr_counts.get(eid, 0) + 1

    blank_counts = {
        eid: sum(1 for s in samples if s.is_blank)
        for eid, samples in samples_by_event.items()
    }
    sample_counts = {eid: len(samples) for eid, samples in samples_by_event.items()}

    return render_template(
        "events/list.html",
        events=events,
        amr_counts=amr_counts,
        blank_counts=blank_counts,
        sample_counts=sample_counts,
    )


@events_bp.route("/new", methods=["GET"])
@login_required
def new():
    form = {
        "project_id": "",
        "matrix_code": "",
        "event_date": datetime.utcnow().strftime("%Y-%m-%d"),
        "expected_sample_count": "",
        "notes": "",
    }
    return render_template(
        "events/new.html",
        form=form,
        available_projects=Project.query.order_by(Project.project_number).all(),
        matrix_code_options=MATRIX_CODE_OPTIONS,
    )


@events_bp.route("/new", methods=["POST"])
@login_required
def create():
    form = {
        "project_id": (request.form.get("project_id") or "").strip(),
        "matrix_code": (request.form.get("matrix_code") or "").strip().upper(),
        "event_date": (request.form.get("event_date") or "").strip(),
        "expected_sample_count": (request.form.get("expected_sample_count") or "").strip(),
        "notes": (request.form.get("notes") or "").strip(),
    }

    errors = []
    try:
        project_id = int(form["project_id"]) if form["project_id"] else None
    except ValueError:
        project_id = None
    if not project_id:
        errors.append("Project is required.")
    if form["matrix_code"] not in MATRIX_CODE_OPTIONS:
        errors.append("Matrix is required.")
    try:
        expected_count = int(form["expected_sample_count"]) if form["expected_sample_count"] else 0
    except ValueError:
        expected_count = 0
    if expected_count < 1:
        errors.append("Expected sample count must be at least 1.")

    project = Project.query.get(project_id) if project_id else None
    if project is None and project_id is not None:
        errors.append("Selected project does not exist.")

    if errors:
        for msg in errors:
            flash(msg, "error")
        return render_template(
            "events/new.html",
            form=form,
            available_projects=Project.query.order_by(Project.project_number).all(),
            matrix_code_options=MATRIX_CODE_OPTIONS,
        ), 400

    event = SamplingEvent(
        project_id=project.id,
        matrix_code=form["matrix_code"],
        event_date=form["event_date"] or None,
        expected_sample_count=expected_count,
        notes=form["notes"] or None,
        created_by_user_id=current_user.id,
    )
    db.session.add(event)
    db.session.flush()

    matrix_label = matrix_from_code(form["matrix_code"])
    for _ in range(expected_count):
        seq = next_sequence_number(project.id, form["matrix_code"])
        client_sample_id = generate_sample_id(project.project_number, form["matrix_code"], seq)
        sample = Sample(
            project_id=project.id,
            sampling_event_id=event.id,
            client_sample_id=client_sample_id,
            matrix=matrix_label,
            matrix_code=form["matrix_code"],
            sequence_number=seq,
            is_blank=False,
        )
        db.session.add(sample)
        db.session.flush()

    db.session.commit()
    flash(f"Created event and generated {expected_count} sample ID(s).", "success")
    return redirect(url_for("events.detail", id=event.id))


@events_bp.route("/<int:id>", methods=["GET"])
@login_required
def detail(id):
    event = SamplingEvent.query.get_or_404(id)
    samples = sorted(event.samples, key=lambda s: (s.sequence_number or 0))

    sample_ids = [s.client_sample_id for s in samples if s.client_sample_id]
    amr_by_sample_id = {}
    if sample_ids:
        amrs = AirMonitorReport.query.filter(
            AirMonitorReport.client_sample_id.in_(sample_ids)
        ).all()
        amr_by_sample_id = {a.client_sample_id: a for a in amrs}

    amr_forms = {}
    for s in samples:
        amr = amr_by_sample_id.get(s.client_sample_id)
        if amr is not None:
            amr_forms[s.id] = _form_from_amr(amr)

    blanks_count = sum(1 for s in samples if s.is_blank)
    amr_count = len(amr_by_sample_id)

    return render_template(
        "events/detail.html",
        event=event,
        samples=samples,
        amr_by_sample_id=amr_by_sample_id,
        amr_forms=amr_forms,
        blanks_count=blanks_count,
        amr_count=amr_count,
        phase_options=PHASE_OPTIONS,
        am_pm_options=AM_PM_OPTIONS,
        temp_unit_options=TEMP_UNIT_OPTIONS,
        available_projects=Project.query.order_by(Project.project_number).all(),
    )


@events_bp.route("/<int:event_id>/sample/<int:sample_id>/toggle-blank", methods=["POST"])
@login_required
def toggle_blank(event_id, sample_id):
    sample = Sample.query.get_or_404(sample_id)
    if sample.sampling_event_id != event_id:
        return jsonify({"status": "error", "message": "Sample not in event."}), 400

    payload = request.get_json(silent=True) or {}
    is_blank = bool(payload.get("is_blank"))

    sample.is_blank = is_blank

    had_amr_deleted = False
    if is_blank:
        existing_amr = AirMonitorReport.query.filter_by(
            client_sample_id=sample.client_sample_id
        ).first()
        if existing_amr is not None:
            db.session.delete(existing_amr)
            had_amr_deleted = True

    db.session.commit()
    return jsonify({
        "status": "ok",
        "is_blank": sample.is_blank,
        "had_amr_deleted": had_amr_deleted,
    })


@events_bp.route("/<int:event_id>/sample/<int:sample_id>/create-amr", methods=["POST"])
@login_required
def create_amr(event_id, sample_id):
    sample = Sample.query.get_or_404(sample_id)
    if sample.sampling_event_id != event_id:
        return jsonify({"status": "error", "message": "Sample not in event."}), 400

    event = SamplingEvent.query.get_or_404(event_id)

    existing = AirMonitorReport.query.filter_by(
        client_sample_id=sample.client_sample_id
    ).first()
    if existing is not None:
        amr = existing
    else:
        amr = AirMonitorReport(
            client_sample_id=sample.client_sample_id,
            project_id=sample.project_id,
            job_number=sample.project.project_number if sample.project else None,
            monitoring_date=event.event_date,
            is_personal_sample=(event.matrix_code == "PM"),
            is_area_sample=(event.matrix_code == "AM"),
            created_by_user_id=current_user.id,
        )
        db.session.add(amr)
        db.session.commit()

    form = _form_from_amr(amr)
    html = render_template(
        "events/_inline_amr_form.html",
        form=form,
        amr=amr,
        sample=sample,
        event=event,
        available_projects=Project.query.order_by(Project.project_number).all(),
        phase_options=PHASE_OPTIONS,
        am_pm_options=AM_PM_OPTIONS,
        temp_unit_options=TEMP_UNIT_OPTIONS,
    )
    return jsonify({"status": "ok", "amr_id": amr.id, "html": html})


def _form_from_amr(amr):
    return {
        "client_sample_id": amr.client_sample_id or "",
        "project_id": amr.project_id or "",
        "job_number": amr.job_number or "",
        "monitoring_date": amr.monitoring_date or "",
        "pump_serial": amr.pump_serial or "",
        "cassette_number": amr.cassette_number or "",
        "monitoring_phase": amr.monitoring_phase or "",
        "time_started": amr.time_started or "",
        "am_pm_started": amr.am_pm_started or "AM",
        "time_stopped": amr.time_stopped or "",
        "am_pm_stopped": amr.am_pm_stopped or "AM",
        "total_hours": amr.total_hours if amr.total_hours is not None else "",
        "total_minutes": amr.total_minutes if amr.total_minutes is not None else "",
        "liters_per_minute": amr.liters_per_minute or "",
        "calibrated_before": bool(amr.calibrated_before),
        "calibrated_before_rate": amr.calibrated_before_rate or "",
        "calibrated_before_by": amr.calibrated_before_by or "",
        "calibrated_after": bool(amr.calibrated_after),
        "calibrated_after_rate": amr.calibrated_after_rate or "",
        "calibrated_after_by": amr.calibrated_after_by or "",
        "last_calibration_date": amr.last_calibration_date or "",
        "measured_rate": amr.measured_rate or "",
        "used_since_calibration": bool(amr.used_since_calibration),
        "is_personal_sample": bool(amr.is_personal_sample),
        "is_area_sample": bool(amr.is_area_sample),
        "worker_monitored": amr.worker_monitored or "",
        "job_duties": amr.job_duties or "",
        "ppe_worn": amr.ppe_worn or "",
        "cassette_worn_properly": bool(amr.cassette_worn_properly),
        "dragged_through_abrasive": bool(amr.dragged_through_abrasive),
        "unusual_happened": bool(amr.unusual_happened),
        "unusual_details": amr.unusual_details or "",
        "monitor_location": amr.monitor_location or "",
        "blasting_location": amr.blasting_location or "",
        "area_unusual_events": amr.area_unusual_events or "",
        "weather_conditions": amr.weather_conditions or "",
        "temperature_value": amr.temperature_value or "",
        "temperature_unit": amr.temperature_unit or "F",
        "wind_speed_direction": amr.wind_speed_direction or "",
        "placed_by": amr.placed_by or "",
        "removed_by": amr.removed_by or "",
        "laboratory_sent_to": amr.laboratory_sent_to or "",
        "date_sent_to_lab": amr.date_sent_to_lab or "",
    }

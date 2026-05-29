from datetime import datetime

from flask import Blueprint, flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from models import AirMonitorReport, FieldSampleRecord, Project, Result, Sample, SamplingEvent, db
from routes.fsr import ALLOWED_AREA_TYPES
from utils.sample_id import (
    MATRIX_CODE_OPTIONS,
    MATRIX_CODE_TO_MATRIX,
    generate_sample_id,
    matrix_from_code,
    next_sequence_number,
)

events_bp = Blueprint("events", __name__, url_prefix="/events")


PHASE_OPTIONS = ("Before", "During", "After")
AM_PM_OPTIONS = ("AM", "PM")
TEMP_UNIT_OPTIONS = ("F", "C")


def needs_amr(matrix_code):
    if not matrix_code:
        return False
    return matrix_code.upper() in ("PM", "AM")


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
        matrix_options=sorted(MATRIX_CODE_TO_MATRIX.items()),
    )


@events_bp.route("/new", methods=["POST"])
@login_required
def create():
    matrix_code = request.form.get("matrix_code", "").strip().upper()
    form = {
        "project_id": (request.form.get("project_id") or "").strip(),
        "matrix_code": matrix_code,
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
    if not form["matrix_code"]:
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
            matrix_options=sorted(MATRIX_CODE_TO_MATRIX.items()),
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
    fsr_by_sample_id = {}
    if sample_ids:
        amrs = AirMonitorReport.query.filter(
            AirMonitorReport.client_sample_id.in_(sample_ids)
        ).all()
        amr_by_sample_id = {a.client_sample_id: a for a in amrs}

        fsrs = FieldSampleRecord.query.filter(
            FieldSampleRecord.client_sample_id.in_(sample_ids)
        ).all()
        fsr_by_sample_id = {f.client_sample_id: f for f in fsrs}

    amr_forms = {}
    fsr_forms = {}
    for s in samples:
        amr = amr_by_sample_id.get(s.client_sample_id)
        if amr is not None:
            amr_forms[s.id] = _form_from_amr(amr)
        fsr = fsr_by_sample_id.get(s.client_sample_id)
        if fsr is not None:
            fsr_forms[s.id] = _form_from_fsr(fsr)

    blanks_count = sum(1 for s in samples if s.is_blank)
    amr_count = len(amr_by_sample_id)
    fsr_count = len(fsr_by_sample_id)

    sample_pk_ids = [s.id for s in samples]
    result_count = 0
    if sample_pk_ids:
        result_count = (
            db.session.query(db.func.count(Result.id))
            .filter(Result.sample_id.in_(sample_pk_ids))
            .scalar()
            or 0
        )

    form_type = "amr" if needs_amr(event.matrix_code) else "fsr"

    return render_template(
        "events/detail.html",
        event=event,
        samples=samples,
        amr_by_sample_id=amr_by_sample_id,
        amr_forms=amr_forms,
        fsr_by_sample_id=fsr_by_sample_id,
        fsr_forms=fsr_forms,
        blanks_count=blanks_count,
        amr_count=amr_count,
        fsr_count=fsr_count,
        result_count=result_count,
        form_type=form_type,
        phase_options=PHASE_OPTIONS,
        am_pm_options=AM_PM_OPTIONS,
        temp_unit_options=TEMP_UNIT_OPTIONS,
        area_types=ALLOWED_AREA_TYPES,
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
    had_fsr_deleted = False
    if is_blank:
        existing_amr = AirMonitorReport.query.filter_by(
            client_sample_id=sample.client_sample_id
        ).first()
        if existing_amr is not None:
            db.session.delete(existing_amr)
            had_amr_deleted = True

        existing_fsr = FieldSampleRecord.query.filter_by(
            client_sample_id=sample.client_sample_id
        ).first()
        if existing_fsr is not None:
            db.session.delete(existing_fsr)
            had_fsr_deleted = True

    db.session.commit()
    return jsonify({
        "status": "ok",
        "is_blank": sample.is_blank,
        "had_amr_deleted": had_amr_deleted,
        "had_fsr_deleted": had_fsr_deleted,
        "had_record_deleted": had_amr_deleted or had_fsr_deleted,
    })


@events_bp.route("/<int:event_id>/delete", methods=["POST"])
@login_required
def delete_event(event_id):
    event = SamplingEvent.query.get_or_404(event_id)

    samples_deleted = 0
    amrs_deleted = 0
    fsrs_deleted = 0
    results_deleted = 0

    for sample in list(event.samples):
        amrs = AirMonitorReport.query.filter_by(
            client_sample_id=sample.client_sample_id
        ).all()
        for amr in amrs:
            db.session.delete(amr)
            amrs_deleted += 1

        fsrs = FieldSampleRecord.query.filter_by(
            client_sample_id=sample.client_sample_id
        ).all()
        for fsr in fsrs:
            db.session.delete(fsr)
            fsrs_deleted += 1

        results = Result.query.filter_by(sample_id=sample.id).all()
        for result in results:
            db.session.delete(result)
            results_deleted += 1

        db.session.delete(sample)
        samples_deleted += 1

    db.session.delete(event)
    db.session.commit()
    flash(
        f"Deleted event: {samples_deleted} samples, {amrs_deleted} field reports, "
        f"{results_deleted} analytical results, {fsrs_deleted} field sample records removed.",
        "success",
    )
    return redirect(url_for("events.list_events"))


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


@events_bp.route("/<int:event_id>/sample/<int:sample_id>/create-fsr", methods=["POST"])
@login_required
def create_fsr(event_id, sample_id):
    sample = Sample.query.get_or_404(sample_id)
    if sample.sampling_event_id != event_id:
        return jsonify({"status": "error", "message": "Sample not in event."}), 400

    event = SamplingEvent.query.get_or_404(event_id)

    existing = FieldSampleRecord.query.filter_by(
        client_sample_id=sample.client_sample_id
    ).first()
    if existing is not None:
        fsr = existing
    else:
        fsr = FieldSampleRecord(
            client_sample_id=sample.client_sample_id,
            project_id=sample.project_id,
            job_number=sample.project.project_number if sample.project else None,
            collection_date=event.event_date,
            created_by_user_id=current_user.id,
        )
        db.session.add(fsr)
        db.session.commit()

    form = _form_from_fsr(fsr)
    html = render_template(
        "events/_inline_fsr_form.html",
        form=form,
        fsr=fsr,
        sample=sample,
        event=event,
        area_types=ALLOWED_AREA_TYPES,
        available_projects=Project.query.order_by(Project.project_number).all(),
    )
    return jsonify({"status": "ok", "fsr_id": fsr.id, "html": html})


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
        "area_type": fsr.area_type or "",
        "analytical_methods_requested": fsr.analytical_methods_requested or "",
        "laboratory_sent_to": fsr.laboratory_sent_to or "",
        "date_sent_to_lab": fsr.date_sent_to_lab or "",
        "general_notes": fsr.general_notes or "",
    }


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

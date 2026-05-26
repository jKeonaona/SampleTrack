from datetime import datetime

from flask import Blueprint, abort, flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from models import AirMonitorReport, Project, Sample, db

amr_bp = Blueprint("amr", __name__, url_prefix="/amr")


PHASE_OPTIONS = ("Before", "During", "After")
AM_PM_OPTIONS = ("AM", "PM")
TEMP_UNIT_OPTIONS = ("F", "C")


def _empty_form():
    return {
        "client_sample_id": "",
        "project_id": "",
        "job_number": "",
        "monitoring_date": "",
        "pump_serial": "",
        "cassette_number": "",
        "monitoring_phase": "",
        "time_started": "",
        "am_pm_started": "AM",
        "time_stopped": "",
        "am_pm_stopped": "AM",
        "total_hours": "",
        "total_minutes": "",
        "liters_per_minute": "",
        "calibrated_before": False,
        "calibrated_before_rate": "",
        "calibrated_before_by": "",
        "calibrated_after": False,
        "calibrated_after_rate": "",
        "calibrated_after_by": "",
        "last_calibration_date": "",
        "measured_rate": "",
        "used_since_calibration": False,
        "is_personal_sample": False,
        "is_area_sample": False,
        "worker_monitored": "",
        "job_duties": "",
        "ppe_worn": "",
        "cassette_worn_properly": False,
        "dragged_through_abrasive": False,
        "unusual_happened": False,
        "unusual_details": "",
        "monitor_location": "",
        "blasting_location": "",
        "area_unusual_events": "",
        "weather_conditions": "",
        "temperature_value": "",
        "temperature_unit": "F",
        "wind_speed_direction": "",
        "placed_by": "",
        "removed_by": "",
        "laboratory_sent_to": "",
        "date_sent_to_lab": "",
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


def _parse_int(value):
    if value is None:
        return None
    s = str(value).strip()
    if not s:
        return None
    try:
        return int(s)
    except ValueError:
        return None


def _form_from_request():
    form = request.form
    sample_type = (form.get("sample_type") or "").strip().lower()
    is_personal = sample_type == "personal"
    is_area = sample_type == "area"
    return {
        "client_sample_id": (form.get("client_sample_id") or "").strip(),
        "project_id": (form.get("project_id") or "").strip(),
        "job_number": (form.get("job_number") or "").strip(),
        "monitoring_date": (form.get("monitoring_date") or "").strip(),
        "pump_serial": (form.get("pump_serial") or "").strip(),
        "cassette_number": (form.get("cassette_number") or "").strip(),
        "monitoring_phase": (form.get("monitoring_phase") or "").strip(),
        "time_started": (form.get("time_started") or "").strip(),
        "am_pm_started": (form.get("am_pm_started") or "").strip(),
        "time_stopped": (form.get("time_stopped") or "").strip(),
        "am_pm_stopped": (form.get("am_pm_stopped") or "").strip(),
        "total_hours": (form.get("total_hours") or "").strip(),
        "total_minutes": (form.get("total_minutes") or "").strip(),
        "liters_per_minute": (form.get("liters_per_minute") or "").strip(),
        "calibrated_before": form.get("calibrated_before") == "on",
        "calibrated_before_rate": (form.get("calibrated_before_rate") or "").strip(),
        "calibrated_before_by": (form.get("calibrated_before_by") or "").strip(),
        "calibrated_after": form.get("calibrated_after") == "on",
        "calibrated_after_rate": (form.get("calibrated_after_rate") or "").strip(),
        "calibrated_after_by": (form.get("calibrated_after_by") or "").strip(),
        "last_calibration_date": (form.get("last_calibration_date") or "").strip(),
        "measured_rate": (form.get("measured_rate") or "").strip(),
        "used_since_calibration": form.get("used_since_calibration") == "on",
        "is_personal_sample": is_personal,
        "is_area_sample": is_area,
        "worker_monitored": (form.get("worker_monitored") or "").strip(),
        "job_duties": (form.get("job_duties") or "").strip(),
        "ppe_worn": (form.get("ppe_worn") or "").strip(),
        "cassette_worn_properly": form.get("cassette_worn_properly") == "on",
        "dragged_through_abrasive": form.get("dragged_through_abrasive") == "on",
        "unusual_happened": form.get("unusual_happened") == "on",
        "unusual_details": (form.get("unusual_details") or "").strip(),
        "monitor_location": (form.get("monitor_location") or "").strip(),
        "blasting_location": (form.get("blasting_location") or "").strip(),
        "area_unusual_events": (form.get("area_unusual_events") or "").strip(),
        "weather_conditions": (form.get("weather_conditions") or "").strip(),
        "temperature_value": (form.get("temperature_value") or "").strip(),
        "temperature_unit": (form.get("temperature_unit") or "F").strip(),
        "wind_speed_direction": (form.get("wind_speed_direction") or "").strip(),
        "placed_by": (form.get("placed_by") or "").strip(),
        "removed_by": (form.get("removed_by") or "").strip(),
        "laboratory_sent_to": (form.get("laboratory_sent_to") or "").strip(),
        "date_sent_to_lab": (form.get("date_sent_to_lab") or "").strip(),
    }


def _apply_form_to_amr(amr, form):
    project_id_raw = form.get("project_id") or ""
    try:
        project_id = int(project_id_raw) if project_id_raw else None
    except ValueError:
        project_id = None

    amr.client_sample_id = form["client_sample_id"]
    amr.project_id = project_id
    amr.job_number = form["job_number"] or None
    amr.monitoring_date = form["monitoring_date"] or None
    amr.pump_serial = form["pump_serial"] or None
    amr.cassette_number = form["cassette_number"] or None
    amr.monitoring_phase = form["monitoring_phase"] or None
    amr.time_started = form["time_started"] or None
    amr.am_pm_started = form["am_pm_started"] or None
    amr.time_stopped = form["time_stopped"] or None
    amr.am_pm_stopped = form["am_pm_stopped"] or None
    amr.total_hours = _parse_int(form["total_hours"])
    amr.total_minutes = _parse_int(form["total_minutes"])
    amr.liters_per_minute = form["liters_per_minute"] or None
    amr.calibrated_before = bool(form["calibrated_before"])
    amr.calibrated_before_rate = form["calibrated_before_rate"] or None
    amr.calibrated_before_by = form["calibrated_before_by"] or None
    amr.calibrated_after = bool(form["calibrated_after"])
    amr.calibrated_after_rate = form["calibrated_after_rate"] or None
    amr.calibrated_after_by = form["calibrated_after_by"] or None
    amr.last_calibration_date = form["last_calibration_date"] or None
    amr.measured_rate = form["measured_rate"] or None
    amr.used_since_calibration = bool(form["used_since_calibration"])
    amr.is_personal_sample = bool(form["is_personal_sample"])
    amr.is_area_sample = bool(form["is_area_sample"])
    amr.worker_monitored = form["worker_monitored"] or None
    amr.job_duties = form["job_duties"] or None
    amr.ppe_worn = form["ppe_worn"] or None
    amr.cassette_worn_properly = bool(form["cassette_worn_properly"])
    amr.dragged_through_abrasive = bool(form["dragged_through_abrasive"])
    amr.unusual_happened = bool(form["unusual_happened"])
    amr.unusual_details = form["unusual_details"] or None
    amr.monitor_location = form["monitor_location"] or None
    amr.blasting_location = form["blasting_location"] or None
    amr.area_unusual_events = form["area_unusual_events"] or None
    amr.weather_conditions = form["weather_conditions"] or None
    amr.temperature_value = form["temperature_value"] or None
    amr.temperature_unit = form["temperature_unit"] or None
    amr.wind_speed_direction = form["wind_speed_direction"] or None
    amr.placed_by = form["placed_by"] or None
    amr.removed_by = form["removed_by"] or None
    amr.laboratory_sent_to = form["laboratory_sent_to"] or None
    amr.date_sent_to_lab = form["date_sent_to_lab"] or None


def _render_form(template, form, amr=None):
    return render_template(
        template,
        form=form,
        amr=amr,
        available_projects=Project.query.order_by(Project.project_number).all(),
        phase_options=PHASE_OPTIONS,
        am_pm_options=AM_PM_OPTIONS,
        temp_unit_options=TEMP_UNIT_OPTIONS,
    )


@amr_bp.route("", methods=["GET"])
@amr_bp.route("/", methods=["GET"])
@login_required
def list_amr():
    reports = AirMonitorReport.query.order_by(AirMonitorReport.created_at.desc()).all()

    sample_ids = {r.client_sample_id for r in reports if r.client_sample_id}
    linked = set()
    if sample_ids:
        existing = (
            db.session.query(Sample.client_sample_id)
            .filter(Sample.client_sample_id.in_(sample_ids))
            .distinct()
            .all()
        )
        linked = {row[0] for row in existing}

    return render_template(
        "amr/list.html",
        reports=reports,
        linked_sample_ids=linked,
    )


@amr_bp.route("/new", methods=["GET"])
@login_required
def new():
    form = _empty_form()
    prefill = (request.args.get("client_sample_id") or "").strip()
    if prefill:
        form["client_sample_id"] = prefill
    return _render_form("amr/new.html", form)


@amr_bp.route("/new", methods=["POST"])
@login_required
def create():
    form = _form_from_request()
    if not form["client_sample_id"]:
        flash("Client Sample ID is required.", "error")
        return _render_form("amr/new.html", form), 400

    amr = AirMonitorReport(created_by_user_id=current_user.id)
    _apply_form_to_amr(amr, form)
    db.session.add(amr)
    db.session.commit()
    flash("Air Monitor Report created.", "success")
    return redirect(url_for("amr.detail", id=amr.id))


@amr_bp.route("/<int:id>", methods=["GET"])
@login_required
def detail(id):
    amr = AirMonitorReport.query.get_or_404(id)
    linked_sample = Sample.query.filter_by(client_sample_id=amr.client_sample_id).first()
    return render_template(
        "amr/detail.html",
        amr=amr,
        linked_sample=linked_sample,
    )


@amr_bp.route("/<int:id>/edit", methods=["GET"])
@login_required
def edit(id):
    amr = AirMonitorReport.query.get_or_404(id)
    form = _form_from_amr(amr)
    return _render_form("amr/edit.html", form, amr=amr)


@amr_bp.route("/<int:id>/edit", methods=["POST"])
@login_required
def edit_save(id):
    is_ajax = (
        request.headers.get("X-Requested-With") == "XMLHttpRequest"
        or request.is_json
    )
    amr = AirMonitorReport.query.get_or_404(id)
    form = _form_from_request()
    if not form["client_sample_id"]:
        if is_ajax:
            return jsonify({"status": "error", "message": "Client Sample ID is required."}), 400
        flash("Client Sample ID is required.", "error")
        return _render_form("amr/edit.html", form, amr=amr), 400

    _apply_form_to_amr(amr, form)
    db.session.commit()

    if is_ajax:
        return jsonify({
            "status": "ok",
            "saved_at": datetime.utcnow().isoformat(),
        })

    flash("Air Monitor Report updated.", "success")
    return redirect(url_for("amr.detail", id=amr.id))


@amr_bp.route("/<int:id>/delete", methods=["POST"])
@login_required
def delete(id):
    if getattr(current_user, "role", None) != "admin":
        abort(403)
    amr = AirMonitorReport.query.get_or_404(id)
    db.session.delete(amr)
    db.session.commit()
    flash("Air Monitor Report deleted.", "success")
    return redirect(url_for("amr.list_amr"))

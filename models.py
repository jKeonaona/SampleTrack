import re
from datetime import datetime

from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import check_password_hash, generate_password_hash

db = SQLAlchemy()

_STANDARD_ID_RE = re.compile(
    r"^\d+-(PM|AM|SS|ES|WW|PC|WS|SA)-\d+(-[A-Za-z])?(\s+.*)?$"
)


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(200), unique=True, index=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    name = db.Column(db.String(200), nullable=True)
    role = db.Column(db.String(20), default="user")
    active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime, nullable=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def is_admin(self):
        return self.role == "admin"

    @property
    def is_authenticated(self):
        return True

    @property
    def is_active(self):
        return bool(self.active)

    @property
    def is_anonymous(self):
        return False

    def get_id(self):
        return str(self.id)


class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    project_number = db.Column(db.String(50), unique=True, index=True, nullable=False)
    name = db.Column(db.String(200), nullable=False)
    client = db.Column(db.String(200), nullable=True)
    location = db.Column(db.String(200), nullable=True)
    status = db.Column(db.String(20), default="active")
    jurisdiction = db.Column(db.String(20), nullable=False, default="California")
    archived_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    samples = db.relationship("Sample", backref="project", cascade="all, delete-orphan")


class Sample(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey("project.id"), nullable=False, index=True)
    sampling_event_id = db.Column(db.Integer, db.ForeignKey("sampling_event.id"), nullable=True, index=True)
    is_blank = db.Column(db.Boolean, default=False, nullable=False)
    sequence_number = db.Column(db.Integer, nullable=True)
    matrix_code = db.Column(db.String(10), nullable=True, index=True)
    client_sample_id = db.Column(db.String(100), nullable=False, index=True)
    lab_sample_id = db.Column(db.String(100), nullable=True, index=True)
    lab_workorder = db.Column(db.String(100), nullable=True, index=True)
    matrix = db.Column(db.String(50), nullable=False)
    collection_date = db.Column(db.Date, nullable=True)
    collection_time = db.Column(db.String(20), nullable=True)
    collection_start_time = db.Column(db.String(20), nullable=True)
    collection_end_time = db.Column(db.String(20), nullable=True)
    location_description = db.Column(db.Text, nullable=True)
    sample_volume = db.Column(db.String(50), nullable=True)
    pump_flow_rate = db.Column(db.String(50), nullable=True)
    employee_monitored = db.Column(db.String(100), nullable=True)
    employee_task = db.Column(db.String(100), nullable=True)
    employee_name = db.Column(db.String(200), nullable=True)
    work_area = db.Column(db.String(200), nullable=True)
    task_description = db.Column(db.String(200), nullable=True)
    wind_speed = db.Column(db.String(50), nullable=True)
    wind_direction = db.Column(db.String(20), nullable=True)
    weather_conditions = db.Column(db.String(100), nullable=True)
    weather_temperature = db.Column(db.String(20), nullable=True)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    results = db.relationship("Result", backref="sample", cascade="all, delete-orphan")

    @property
    def is_standard_id_format(self):
        """True if client_sample_id matches the canonical <job>-<MATRIX>-<###> format.

        Computed on access — never stored — so editing the ID re-evaluates
        the flag automatically.
        """
        if not self.client_sample_id:
            return False
        return bool(_STANDARD_ID_RE.match(self.client_sample_id))


class Threshold(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    analyte = db.Column(db.String(100), nullable=False, index=True)
    matrix = db.Column(db.String(50), nullable=False, index=True)
    threshold_name = db.Column(db.String(100), nullable=False)
    regulatory_body = db.Column(db.String(50), nullable=False)
    value = db.Column(db.Float, nullable=False)
    units = db.Column(db.String(20), nullable=False)
    notes = db.Column(db.Text, nullable=True)
    active = db.Column(db.Boolean, default=True)
    jurisdiction = db.Column(db.String(20), nullable=False, default="Both")
    threshold_type = db.Column(db.String(20), nullable=False, default="PEL")
    effective_date = db.Column(db.String(20), nullable=True)
    superseded_date = db.Column(db.String(20), nullable=True)
    source_citation = db.Column(db.String(200), nullable=True)
    last_verified_date = db.Column(db.String(20), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.Index("ix_threshold_analyte_matrix", "analyte", "matrix"),
    )


class SamplingEvent(db.Model):
    __tablename__ = "sampling_event"

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey("project.id"), nullable=False, index=True)
    matrix_code = db.Column(db.String(10), nullable=False)
    event_date = db.Column(db.String(20), nullable=True)
    expected_sample_count = db.Column(db.Integer, nullable=True)
    notes = db.Column(db.Text, nullable=True)
    created_by_user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    project = db.relationship("Project", backref="sampling_events")
    samples = db.relationship("Sample", backref="sampling_event", lazy=True)
    created_by = db.relationship("User", foreign_keys=[created_by_user_id])


class AirMonitorReport(db.Model):
    __tablename__ = "air_monitor_report"

    id = db.Column(db.Integer, primary_key=True)
    created_by_user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True, index=True)
    client_sample_id = db.Column(db.String(100), nullable=False, index=True)
    project_id = db.Column(db.Integer, db.ForeignKey("project.id"), nullable=True, index=True)
    job_number = db.Column(db.String(50), nullable=True)

    monitoring_date = db.Column(db.String(20), nullable=True)
    pump_serial = db.Column(db.String(100), nullable=True)
    cassette_number = db.Column(db.String(100), nullable=True)
    monitoring_phase = db.Column(db.String(20), nullable=True)

    time_started = db.Column(db.String(10), nullable=True)
    am_pm_started = db.Column(db.String(2), nullable=True)
    time_stopped = db.Column(db.String(10), nullable=True)
    am_pm_stopped = db.Column(db.String(2), nullable=True)
    total_hours = db.Column(db.Integer, nullable=True)
    total_minutes = db.Column(db.Integer, nullable=True)
    liters_per_minute = db.Column(db.String(20), nullable=True)

    calibrated_before = db.Column(db.Boolean, nullable=True)
    calibrated_before_rate = db.Column(db.String(20), nullable=True)
    calibrated_before_by = db.Column(db.String(100), nullable=True)
    calibrated_after = db.Column(db.Boolean, nullable=True)
    calibrated_after_rate = db.Column(db.String(20), nullable=True)
    calibrated_after_by = db.Column(db.String(100), nullable=True)
    last_calibration_date = db.Column(db.String(20), nullable=True)
    measured_rate = db.Column(db.String(20), nullable=True)
    used_since_calibration = db.Column(db.Boolean, nullable=True)

    is_personal_sample = db.Column(db.Boolean, nullable=True)
    worker_monitored = db.Column(db.String(200), nullable=True)
    job_duties = db.Column(db.Text, nullable=True)
    ppe_worn = db.Column(db.Text, nullable=True)
    cassette_worn_properly = db.Column(db.Boolean, nullable=True)
    dragged_through_abrasive = db.Column(db.Boolean, nullable=True)
    unusual_happened = db.Column(db.Boolean, nullable=True)
    unusual_details = db.Column(db.Text, nullable=True)

    is_area_sample = db.Column(db.Boolean, nullable=True)
    monitor_location = db.Column(db.String(500), nullable=True)
    blasting_location = db.Column(db.String(500), nullable=True)
    area_unusual_events = db.Column(db.Text, nullable=True)
    weather_conditions = db.Column(db.String(500), nullable=True)
    temperature_value = db.Column(db.String(20), nullable=True)
    temperature_unit = db.Column(db.String(2), nullable=True)
    wind_speed_direction = db.Column(db.String(200), nullable=True)

    placed_by = db.Column(db.String(200), nullable=True)
    removed_by = db.Column(db.String(200), nullable=True)
    laboratory_sent_to = db.Column(db.String(200), nullable=True)
    date_sent_to_lab = db.Column(db.String(20), nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    created_by = db.relationship("User", foreign_keys=[created_by_user_id])
    project = db.relationship("Project", foreign_keys=[project_id])


class FieldSampleRecord(db.Model):
    __tablename__ = "field_sample_record"

    id = db.Column(db.Integer, primary_key=True)
    created_by_user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    client_sample_id = db.Column(db.String(100), nullable=False, index=True)
    project_id = db.Column(db.Integer, db.ForeignKey("project.id"), nullable=True)
    job_number = db.Column(db.String(50), nullable=True)

    collection_date = db.Column(db.String(20), nullable=True)
    collection_time = db.Column(db.String(10), nullable=True)
    collected_by = db.Column(db.String(200), nullable=True)
    location_description = db.Column(db.Text, nullable=True)

    matrix_specific_notes = db.Column(db.Text, nullable=True)
    # Allowed: Eating Area, Vehicle, Decon Area, Shower Facility, Clean Room, Restroom, Other. NULL for non-wipe matrices.
    area_type = db.Column(db.String(50), nullable=True)

    analytical_methods_requested = db.Column(db.Text, nullable=True)

    laboratory_sent_to = db.Column(db.String(200), nullable=True)
    date_sent_to_lab = db.Column(db.String(20), nullable=True)

    general_notes = db.Column(db.Text, nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    creator = db.relationship("User", foreign_keys=[created_by_user_id])
    project = db.relationship("Project", foreign_keys=[project_id])


class Result(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sample_id = db.Column(db.Integer, db.ForeignKey("sample.id"), nullable=False, index=True)
    analyte = db.Column(db.String(100), nullable=False, index=True)
    result_value = db.Column(db.String(50), nullable=False)
    result_numeric = db.Column(db.Float, nullable=True)
    result_units = db.Column(db.String(50), nullable=True)
    reporting_limit = db.Column(db.String(50), nullable=True)
    dilution_factor = db.Column(db.String(20), nullable=True)
    method_reference = db.Column(db.String(100), nullable=True)
    extraction_method = db.Column(db.String(50), nullable=True)
    lab_report_number = db.Column(db.String(100), nullable=True, index=True)
    report_date = db.Column(db.Date, nullable=True)
    date_analyzed = db.Column(db.DateTime, nullable=True)
    twa_8hr = db.Column(db.Float, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

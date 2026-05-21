from datetime import datetime

from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import check_password_hash, generate_password_hash

db = SQLAlchemy()


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
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    samples = db.relationship("Sample", backref="project", cascade="all, delete-orphan")


class Sample(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey("project.id"), nullable=False, index=True)
    client_sample_id = db.Column(db.String(100), nullable=False, index=True)
    lab_sample_id = db.Column(db.String(100), nullable=True, index=True)
    lab_workorder = db.Column(db.String(100), nullable=True, index=True)
    matrix = db.Column(db.String(50), nullable=False)
    collection_date = db.Column(db.Date, nullable=True)
    collection_time = db.Column(db.String(20), nullable=True)
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
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.Index("ix_threshold_analyte_matrix", "analyte", "matrix"),
    )


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
    lab_report_number = db.Column(db.String(100), nullable=True, index=True)
    report_date = db.Column(db.Date, nullable=True)
    date_analyzed = db.Column(db.DateTime, nullable=True)
    twa_8hr = db.Column(db.Float, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

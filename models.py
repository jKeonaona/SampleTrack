from datetime import datetime

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


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
    wind_speed = db.Column(db.String(50), nullable=True)
    wind_direction = db.Column(db.String(20), nullable=True)
    weather_conditions = db.Column(db.String(100), nullable=True)
    weather_temperature = db.Column(db.String(20), nullable=True)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    results = db.relationship("Result", backref="sample", cascade="all, delete-orphan")


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

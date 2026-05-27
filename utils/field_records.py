"""Shared helpers for linking Samples to Sampling Events and field records.

Used by both the legacy backfill script and the PDF upload flow so that new
samples always get an event + field-record stub (AMR for air matrices, FSR
for everything else).

Functions here do not commit. Callers control transaction boundaries.
"""

import re

from models import AirMonitorReport, FieldSampleRecord, SamplingEvent, db


# Sample.matrix -> two-letter code. Accepts both canonical and alias spellings.
MATRIX_CODE_MAP = {
    "Personal Air": "PM",
    "Area Air": "AM",
    "Wipe": "WS",
    "Soil": "SS",
    "Excavated Soil": "ES",
    "Paint Chip": "PC",
    "Spent Abrasive": "SA",
    "Spent Abrasives": "SA",
    "Liquid": "WW",
    "Waste Water": "WW",
}

# Reverse map for parser use: code -> canonical matrix name.
# Uses the canonical spellings (no plural, "Liquid" not "Waste Water").
CODE_TO_MATRIX = {
    "PM": "Personal Air",
    "AM": "Area Air",
    "WS": "Wipe",
    "SS": "Soil",
    "ES": "Excavated Soil",
    "PC": "Paint Chip",
    "SA": "Spent Abrasive",
    "WW": "Liquid",
}

AIR_MATRICES = ("Personal Air", "Area Air")

_NUMBER_RE = re.compile(r"-?\d+\.?\d*")


def parse_numeric(value):
    """Pull the first numeric token out of a free-form string like '2.0 L/min'."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    match = _NUMBER_RE.search(str(value).strip())
    if match is None:
        return None
    try:
        return float(match.group())
    except (TypeError, ValueError):
        return None


def matrix_code_for(matrix):
    if not matrix:
        return "UN"
    return MATRIX_CODE_MAP.get(matrix, "UN")


def matrix_name_for_code(code):
    """Reverse lookup. Returns 'Other' if the code is unknown."""
    if not code:
        return "Other"
    return CODE_TO_MATRIX.get(code.upper(), "Other")


def event_date_str(collection_date):
    """Sample.collection_date is a Date; SamplingEvent.event_date is a String."""
    if collection_date is None:
        return None
    if hasattr(collection_date, "isoformat"):
        return collection_date.isoformat()
    return str(collection_date)


def ensure_event_for_sample(sample):
    """Find or create the SamplingEvent for this sample's (project, matrix, date).

    Side effects on `sample`:
      - sets sample.sampling_event_id (if not already set)
      - sets sample.matrix_code (if not already set)

    Returns (event, created) — created is True if a new SamplingEvent row was
    inserted, False if an existing event was reused. Returns (None, False)
    when the sample is missing a project_id.
    """
    if sample.project_id is None:
        return None, False

    code = sample.matrix_code or matrix_code_for(sample.matrix)
    event_date = event_date_str(sample.collection_date)

    if sample.sampling_event_id is not None:
        event = SamplingEvent.query.get(sample.sampling_event_id)
        if event is not None:
            if not sample.matrix_code:
                sample.matrix_code = code
            return event, False

    existing = (
        SamplingEvent.query
        .filter_by(
            project_id=sample.project_id,
            matrix_code=code,
            event_date=event_date,
        )
        .first()
    )

    created = False
    if existing is None:
        existing = SamplingEvent(
            project_id=sample.project_id,
            matrix_code=code,
            event_date=event_date,
            expected_sample_count=None,
            notes="Auto-created during lab report upload.",
        )
        db.session.add(existing)
        db.session.flush()
        created = True

    sample.sampling_event_id = existing.id
    if not sample.matrix_code:
        sample.matrix_code = code
    return existing, created


def ensure_field_record_for_sample(sample):
    """Create an AMR (air) or FSR (non-air) stub if none exists yet.

    Matches by client_sample_id (the join key). Returns (record, created) —
    created is True if a new row was inserted, False if an existing record
    was reused. Returns (None, False) if there's no client_sample_id or
    matrix to act on.
    """
    if not sample.client_sample_id:
        return None, False

    is_air = sample.matrix in AIR_MATRICES
    monitoring_date = event_date_str(sample.collection_date)

    if is_air:
        existing = (
            AirMonitorReport.query
            .filter_by(client_sample_id=sample.client_sample_id)
            .first()
        )
        if existing is not None:
            return existing, False

        flow_numeric = parse_numeric(sample.pump_flow_rate)
        amr = AirMonitorReport(
            client_sample_id=sample.client_sample_id,
            project_id=sample.project_id,
            monitoring_date=monitoring_date,
            time_started=sample.collection_start_time,
            time_stopped=sample.collection_end_time,
            liters_per_minute=f"{flow_numeric}" if flow_numeric is not None else None,
            is_personal_sample=(sample.matrix == "Personal Air"),
            is_area_sample=(sample.matrix == "Area Air"),
            worker_monitored=(sample.employee_name if sample.matrix == "Personal Air" else None),
            job_duties=(sample.task_description if sample.matrix == "Personal Air" else None),
            monitor_location=(sample.work_area if sample.matrix == "Area Air" else None),
        )
        db.session.add(amr)
        return amr, True

    if not sample.matrix:
        return None, False

    existing = (
        FieldSampleRecord.query
        .filter_by(client_sample_id=sample.client_sample_id)
        .first()
    )
    if existing is not None:
        return existing, False

    fsr = FieldSampleRecord(
        client_sample_id=sample.client_sample_id,
        project_id=sample.project_id,
        collection_date=monitoring_date,
        collection_time=sample.collection_start_time,
        collected_by=None,
        location_description=sample.work_area,
        matrix_specific_notes=sample.task_description,
        general_notes="Auto-created during lab report upload.",
    )
    db.session.add(fsr)
    return fsr, True

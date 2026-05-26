from models import Sample, db


MATRIX_CODE_TO_MATRIX = {
    "AM": "Area Air",
    "PM": "Personal Air",
    "SS": "Soil",
    "ES": "Excavated Soil",
    "WW": "Liquid",
    "PC": "Paint Chip",
    "WS": "Wipe",
    "SA": "Spent Abrasive",
}

MATRIX_CODE_OPTIONS = ["PM", "AM", "SS", "ES", "WW", "PC", "WS", "SA"]


def next_sequence_number(project_id, matrix_code):
    """Return next sequence for this project+matrix. Queries MAX(sequence_number)."""
    max_seq = db.session.query(db.func.max(Sample.sequence_number)).filter(
        Sample.project_id == project_id,
        Sample.matrix_code == matrix_code,
    ).scalar()
    return (max_seq or 0) + 1


def generate_sample_id(project_number, matrix_code, sequence):
    """Format: <project_number>-<matrix_code>-<4-digit-seq>."""
    return f"{project_number}-{matrix_code}-{sequence:04d}"


def matrix_from_code(matrix_code):
    if not matrix_code:
        return "Other"
    return MATRIX_CODE_TO_MATRIX.get(matrix_code.upper(), "Other")


MERGEABLE_FIELDS = [
    "lab_workorder",
    "lab_sample_id",
    "collection_time",
    "collection_start_time",
    "collection_end_time",
    "sample_volume",
    "pump_flow_rate",
]


def merge_lab_data_into_sample(existing_sample, sample_data):
    """Populate an empty field on an event-created Sample stub with lab data.

    Only fills fields that are currently empty (None or empty string) on the
    existing sample. Never overwrites manually-entered data. Identity fields
    (id, client_sample_id, project_id, sampling_event_id, sequence_number,
    is_blank, matrix_code, created_at) are never touched.
    """
    from routes.projects import _parse_date

    for field in MERGEABLE_FIELDS:
        if not getattr(existing_sample, field, None):
            new_val = sample_data.get(field)
            if new_val:
                setattr(existing_sample, field, new_val)

    if not existing_sample.collection_date:
        raw_date = sample_data.get("collection_date")
        parsed = _parse_date(raw_date) if raw_date else None
        if parsed is not None:
            existing_sample.collection_date = parsed

    if not existing_sample.matrix or existing_sample.matrix == "Other":
        new_matrix = sample_data.get("matrix")
        if new_matrix:
            existing_sample.matrix = new_matrix

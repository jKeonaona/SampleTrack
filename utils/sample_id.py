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

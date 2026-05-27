import os
import sys
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import inspect, text

from app import app
from models import Threshold, db


COLUMNS = [
    ("effective_date", "VARCHAR(20)"),
    ("superseded_date", "VARCHAR(20)"),
    ("source_citation", "VARCHAR(200)"),
    ("last_verified_date", "VARCHAR(20)"),
]


# Patterns are matched (case-insensitive) against "threshold_name | regulatory_body".
# First match wins, so order matters — put more specific patterns above generic ones.
PRESETS = [
    ("Cal/OSHA Personal Air PEL", ("2025-01-01", "Cal/OSHA Title 8 §1532.1(c)")),
    ("Cal/OSHA Personal Air Action Level", ("2025-01-01", "Cal/OSHA Title 8 §1532.1(b)")),
    ("Cal/OSHA Personal Air AL", ("2025-01-01", "Cal/OSHA Title 8 §1532.1(b)")),
    ("Cal/OSHA Abrasive Blasting", ("2025-01-01", "Cal/OSHA Title 8 §1532.1(c)(2)")),

    ("Fed OSHA PEL", ("1993-06-03", "29 CFR 1926.62")),
    ("Fed OSHA Action Level", ("1993-06-03", "29 CFR 1926.62")),
    ("Fed OSHA AL", ("1993-06-03", "29 CFR 1926.62")),

    ("EPA NAAQS", ("2008-10-15", "40 CFR 50.16")),
    ("CARB CAAQS", ("1987-04-17", "17 CCR §70200")),
    ("BAAQMD Reg 11-1-302", ("2017-12-20", "BAAQMD Regulation 11-1-302")),
    ("BAAQMD Reg 11-1-303", ("2017-12-20", "BAAQMD Regulation 11-1-303")),
    ("SCAQMD Rule 1420", ("2010-11-05", "SCAQMD Rule 1420")),

    ("HUD Floor", ("2024-08-19", "24 CFR 35.1320")),
    ("HUD Window Sill", ("2024-08-19", "24 CFR 35.1320")),
    ("HUD Bare Soil", ("2024-08-19", "24 CFR 35.1320")),

    ("CHHSL Residential", ("2009-01-01", "DTSC HHRA Note 3")),

    ("HUD/EPA Lead-Based Paint", ("2001-03-06", "40 CFR 745.65 / 24 CFR 35.86")),
    ("Lead-Based Paint", ("2001-03-06", "40 CFR 745.65 / 24 CFR 35.86")),
]

FALLBACK = ("2000-01-01", "(unknown — needs review)")


def _classify(name, body):
    haystack = f"{name or ''} | {body or ''}".lower()
    for pattern, preset in PRESETS:
        if pattern.lower() in haystack:
            return preset
    return None


def main():
    today_iso = date.today().isoformat()
    with app.app_context():
        inspector = inspect(db.engine)
        existing = {col["name"] for col in inspector.get_columns("threshold")}
        for name, col_type in COLUMNS:
            if name in existing:
                print(f"Skipped (already exists): {name}")
                continue
            db.session.execute(text(f"ALTER TABLE threshold ADD COLUMN {name} {col_type}"))
            db.session.commit()
            print(f"Added column: {name}")

        thresholds = Threshold.query.all()
        backfilled = 0
        fallback_count = 0

        for t in thresholds:
            preset = _classify(t.threshold_name, t.regulatory_body)
            if preset is None:
                eff, cite = FALLBACK
                print(
                    f"  ! fallback used: {t.analyte} / {t.matrix} / "
                    f"{t.threshold_name} / {t.regulatory_body}"
                )
                fallback_count += 1
            else:
                eff, cite = preset

            t.effective_date = eff
            t.source_citation = cite
            t.superseded_date = None
            t.last_verified_date = today_iso
            backfilled += 1

        db.session.commit()

        print(
            f"Backfilled {backfilled} thresholds with effective dates. "
            f"{fallback_count} rows needed fallback (unknown citation)."
        )


if __name__ == "__main__":
    main()

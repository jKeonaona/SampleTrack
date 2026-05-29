"""Seed EPA 2024 Dust-Lead Action Level thresholds for the Wipe matrix.

Source: 89 FR 89416 (Nov 12, 2024), effective Jan 13, 2025. Lowered the
post-abatement Dust-Lead Action Levels per 40 CFR 745.227(e)(8):
  Floor:           10 -> 5  µg/ft²
  Window Sill:    100 -> 40 µg/ft²
  Window Trough:  400 -> 100 µg/ft²

Existing HUD Floor and HUD Window Sill rows are NOT superseded; both
reference sets remain visible alongside each other.
"""

import os
import sys
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app
from models import db, Threshold


TODAY = date.today().isoformat()

COMMON = {
    "analyte": "Lead",
    "matrix": "Wipe",
    "regulatory_body": "EPA",
    "units": "µg/ft²",
    "threshold_type": "Clearance",
    "jurisdiction": "Both",
    "effective_date": "2025-01-13",
    "superseded_date": None,
    "source_citation": "40 CFR 745.227(e)(8); 89 FR 89416 (Nov 12, 2024)",
    "last_verified_date": TODAY,
    "active": True,
}

ROWS = [
    {**COMMON, "threshold_name": "EPA Dust-Lead Action Level - Floor", "value": 5.0},
    {**COMMON, "threshold_name": "EPA Dust-Lead Action Level - Window Sill", "value": 40.0},
    {**COMMON, "threshold_name": "EPA Dust-Lead Action Level - Window Trough", "value": 100.0},
]


def main():
    with app.app_context():
        for row in ROWS:
            existing = Threshold.query.filter_by(
                threshold_name=row["threshold_name"],
                analyte=row["analyte"],
                matrix=row["matrix"],
                regulatory_body=row["regulatory_body"],
            ).first()
            if existing is not None:
                print(f"OK: {row['threshold_name']} already present")
                continue
            db.session.add(Threshold(**row))
            print(f"OK: added {row['threshold_name']}")

        db.session.commit()

        total = Threshold.query.filter_by(analyte="Lead", matrix="Wipe").count()
        print(f"\nFinal Lead/Wipe Threshold rows: {total} (expected 5: 2 HUD + 3 EPA)")


if __name__ == "__main__":
    main()

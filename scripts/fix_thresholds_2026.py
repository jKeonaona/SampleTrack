import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app
from models import db, Threshold


# (analyte, matrix, threshold_name, regulatory_body, new_value, human_label)
VALUE_UPDATES = [
    ("Lead", "Personal Air", "PEL (8-hr TWA)", "Cal/OSHA", 10.0,
     "Cal/OSHA Personal Air PEL 50 → 10"),
    ("Lead", "Personal Air", "Action Level (8-hr TWA)", "Cal/OSHA", 2.0,
     "Cal/OSHA Personal Air Action Level 30 → 2"),
]

# (analyte, matrix, threshold_name, regulatory_body)
AREA_AIR_DELETIONS = [
    ("Lead", "Area Air", "PEL (8-hr TWA)", "Cal/OSHA"),
    ("Lead", "Area Air", "Action Level (8-hr TWA)", "Cal/OSHA"),
    ("Lead", "Area Air", "PEL (8-hr TWA)", "Fed OSHA"),
    ("Lead", "Area Air", "Action Level (8-hr TWA)", "Fed OSHA"),
]

# (analyte, matrix, threshold_name, regulatory_body, value, units)
NEW_THRESHOLDS = [
    ("Lead", "Personal Air", "PEL Abrasive Blasting (until 1/1/2030)", "Cal/OSHA", 25.0, "µg/m³"),
    ("Lead", "Area Air", "NAAQS (rolling 3-month)", "EPA", 0.15, "µg/m³"),
    ("Lead", "Area Air", "CAAQS (30-day average)", "CARB", 1.5, "µg/m³"),
]


def main():
    updated = 0
    deleted = 0
    added = 0

    with app.app_context():
        for analyte, matrix, name, body, new_value, label in VALUE_UPDATES:
            row = Threshold.query.filter_by(
                analyte=analyte,
                matrix=matrix,
                threshold_name=name,
                regulatory_body=body,
            ).first()
            if row is None:
                print(f"Skipped (not found): {label}")
            elif row.value == new_value:
                print(f"Skipped (already {new_value}): {label}")
            else:
                row.value = new_value
                print(f"Updated: {label}")
                updated += 1

        for analyte, matrix, name, body in AREA_AIR_DELETIONS:
            row = Threshold.query.filter_by(
                analyte=analyte,
                matrix=matrix,
                threshold_name=name,
                regulatory_body=body,
            ).first()
            if row is None:
                print(f"Skipped (already removed): {body} {matrix} {name}")
            else:
                db.session.delete(row)
                print(f"Deleted: {body} {matrix} {name}")
                deleted += 1

        for analyte, matrix, name, body, value, units in NEW_THRESHOLDS:
            existing = Threshold.query.filter_by(
                analyte=analyte,
                matrix=matrix,
                threshold_name=name,
                regulatory_body=body,
            ).first()
            if existing is not None:
                print(f"Skipped (already exists): {analyte} / {matrix} / {name} / {body}")
            else:
                db.session.add(Threshold(
                    analyte=analyte,
                    matrix=matrix,
                    threshold_name=name,
                    regulatory_body=body,
                    value=value,
                    units=units,
                    active=True,
                ))
                print(f"Added: {analyte} / {matrix} / {name} / {body}")
                added += 1

        db.session.commit()

    print(f"\nDone. Updated {updated}, deleted {deleted}, added {added}.")


if __name__ == "__main__":
    main()

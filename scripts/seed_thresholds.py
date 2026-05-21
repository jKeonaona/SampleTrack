import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app
from models import db, Threshold


THRESHOLDS = [
    # AIR — PEL and Action Level for both Area Air and Personal Air,
    # for both Cal/OSHA and Fed OSHA
    ("Lead", "Area Air", "PEL (8-hr TWA)", "Cal/OSHA", 50.0, "µg/m³"),
    ("Lead", "Area Air", "Action Level (8-hr TWA)", "Cal/OSHA", 30.0, "µg/m³"),
    ("Lead", "Area Air", "PEL (8-hr TWA)", "Fed OSHA", 50.0, "µg/m³"),
    ("Lead", "Area Air", "Action Level (8-hr TWA)", "Fed OSHA", 30.0, "µg/m³"),
    ("Lead", "Personal Air", "PEL (8-hr TWA)", "Cal/OSHA", 50.0, "µg/m³"),
    ("Lead", "Personal Air", "Action Level (8-hr TWA)", "Cal/OSHA", 30.0, "µg/m³"),
    ("Lead", "Personal Air", "PEL (8-hr TWA)", "Fed OSHA", 50.0, "µg/m³"),
    ("Lead", "Personal Air", "Action Level (8-hr TWA)", "Fed OSHA", 30.0, "µg/m³"),
    # WIPE — HUD clearance
    ("Lead", "Wipe", "HUD Floor Clearance", "HUD", 10.0, "µg/ft²"),
    ("Lead", "Wipe", "HUD Window Sill Clearance", "HUD", 100.0, "µg/ft²"),
    # SOIL
    ("Lead", "Soil", "CHHSL Residential", "CA DTSC", 80.0, "mg/kg"),
    ("Lead", "Soil", "HUD Bare Soil (Residential)", "HUD", 400.0, "mg/kg"),
    # PAINT CHIP
    ("Lead", "Paint Chip", "Lead-Based Paint Threshold", "HUD/EPA", 5000.0, "ppm"),
]


def main():
    added = 0
    skipped = 0
    with app.app_context():
        db.create_all()
        for analyte, matrix, name, body, value, units in THRESHOLDS:
            existing = Threshold.query.filter_by(
                analyte=analyte,
                matrix=matrix,
                threshold_name=name,
                regulatory_body=body,
            ).first()
            if existing is not None:
                print(f"Skipped (already exists): {analyte} / {matrix} / {name} / {body}")
                skipped += 1
                continue
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
    print(f"\nDone. Added {added}, skipped {skipped}.")


if __name__ == "__main__":
    main()

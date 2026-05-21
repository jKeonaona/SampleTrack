import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app
from models import db, Threshold


THRESHOLDS = [
    # AIR — Personal Air (OSHA worker-exposure standards)
    # Cal/OSHA dropped PEL to 10 µg/m³ and Action Level to 2 µg/m³ effective Jan 1, 2025.
    ("Lead", "Personal Air", "PEL (8-hr TWA)", "Cal/OSHA", 10.0, "µg/m³"),
    ("Lead", "Personal Air", "Action Level (8-hr TWA)", "Cal/OSHA", 2.0, "µg/m³"),
    ("Lead", "Personal Air", "PEL Abrasive Blasting (until 1/1/2030)", "Cal/OSHA", 25.0, "µg/m³"),
    ("Lead", "Personal Air", "PEL (8-hr TWA)", "Fed OSHA", 50.0, "µg/m³"),
    ("Lead", "Personal Air", "Action Level (8-hr TWA)", "Fed OSHA", 30.0, "µg/m³"),
    # AIR — Area Air (ambient air-quality standards; OSHA does not apply to area samples)
    ("Lead", "Area Air", "NAAQS (rolling 3-month)", "EPA", 0.15, "µg/m³"),
    ("Lead", "Area Air", "CAAQS (30-day average)", "CARB", 1.5, "µg/m³"),
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

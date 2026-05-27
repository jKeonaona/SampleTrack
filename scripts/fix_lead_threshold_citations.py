import os
import sys
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app
from models import Threshold, db


# (analyte, matrix, threshold_name, regulatory_body, effective_date,
#  superseded_date, source_citation)
UPDATES = [
    ("Lead", "Personal Air", "PEL (8-hr TWA)", "Cal/OSHA",
     "2025-01-01", None, "Cal/OSHA Title 8 §1532.1(c)"),
    ("Lead", "Personal Air", "Action Level (8-hr TWA)", "Cal/OSHA",
     "2025-01-01", None, "Cal/OSHA Title 8 §1532.1(b)"),
    ("Lead", "Personal Air", "PEL (8-hr TWA)", "Fed OSHA",
     "1993-06-03", None, "29 CFR 1926.62(c)"),
    ("Lead", "Personal Air", "Action Level (8-hr TWA)", "Fed OSHA",
     "1993-06-03", None, "29 CFR 1926.62(b)"),
    ("Lead", "Personal Air", "PEL Abrasive Blasting (until 1/1/2030)", "Cal/OSHA",
     "2025-01-01", "2030-01-01", "Cal/OSHA Title 8 §1532.1(c)(2)"),
    ("Lead", "Area Air", "NAAQS (rolling 3-month)", "EPA",
     "2008-10-15", None, "40 CFR 50.16"),
    ("Lead", "Area Air", "CAAQS (30-day average)", "CARB",
     "1976-12-15", None, "17 CCR §70200"),
]


def main():
    today_iso = date.today().isoformat()
    fixed = 0
    missing = []

    with app.app_context():
        for (analyte, matrix, name, body, eff, sup, cite) in UPDATES:
            rows = Threshold.query.filter_by(
                analyte=analyte,
                matrix=matrix,
                threshold_name=name,
                regulatory_body=body,
            ).all()

            if not rows:
                missing.append((analyte, matrix, name, body))
                continue

            for row in rows:
                row.effective_date = eff
                row.superseded_date = sup
                row.source_citation = cite
                row.last_verified_date = today_iso
                fixed += 1

        db.session.commit()

        print(f"Fixed {fixed} threshold row(s).")
        if missing:
            print(f"WARNING: {len(missing)} update(s) had no matching row:")
            for analyte, matrix, name, body in missing:
                print(f"  - {analyte} / {matrix} / {name} / {body}")
        else:
            print("All targeted rows were found and updated.")


if __name__ == "__main__":
    main()

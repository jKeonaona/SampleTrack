"""Seed Spent Abrasive hazardous-waste characterization thresholds for Lead.

Spent abrasive blast media is evaluated for waste classification, not for
airborne exposure. The applicable limits are leaching / total-content
thresholds, not PEL/AL:

  Federal RCRA TCLP (Lead):  5.0 mg/L   per 40 CFR 261.24, Table 1
  California Title 22 STLC:   5.0 mg/L   per 22 CCR §66261.24
  California Title 22 TTLC:   1000 mg/kg per 22 CCR §66261.24

TCLP and STLC are leachate concentrations (mg/L); TTLC is a total
concentration (mg/kg). Unit-aware threshold selection in
utils.calculations.get_applicable_thresholds keeps a leachate result from
being compared against the total-content limit and vice versa.
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
    "matrix": "Spent Abrasive",
    "superseded_date": None,
    "last_verified_date": TODAY,
    "active": True,
}

ROWS = [
    {
        **COMMON,
        "threshold_name": "Federal TCLP - Hazardous Waste Threshold",
        "regulatory_body": "EPA",
        "value": 5.0,
        "units": "mg/L",
        "threshold_type": "TCLP",
        "jurisdiction": "Both",
        "effective_date": "1990-01-01",
        "source_citation": "40 CFR 261.24, Table 1 (Toxicity Characteristic Leaching Procedure)",
    },
    {
        **COMMON,
        "threshold_name": "California STLC - Hazardous Waste Threshold",
        "regulatory_body": "DTSC",
        "value": 5.0,
        "units": "mg/L",
        "threshold_type": "STLC",
        "jurisdiction": "California",
        "effective_date": "1990-01-01",
        "source_citation": "22 CCR §66261.24, Table II (Soluble Threshold Limit Concentration)",
    },
    {
        **COMMON,
        "threshold_name": "California TTLC - Hazardous Waste Threshold",
        "regulatory_body": "DTSC",
        "value": 1000.0,
        "units": "mg/kg",
        "threshold_type": "TTLC",
        "jurisdiction": "California",
        "effective_date": "1990-01-01",
        "source_citation": "22 CCR §66261.24, Table II (Total Threshold Limit Concentration)",
    },
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

        total = Threshold.query.filter_by(analyte="Lead", matrix="Spent Abrasive").count()
        print(f"\nFinal Lead/Spent Abrasive Threshold rows: {total} (expected 3 minimum)")


if __name__ == "__main__":
    main()

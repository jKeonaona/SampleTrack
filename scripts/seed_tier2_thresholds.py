import os
import sys
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app
from models import Threshold, db


TIER2_THRESHOLDS = [
    # ===== TOLUENE — Cal/OSHA §5155 Table AC-1, Fed OSHA 29 CFR 1910.1000 Z-1 =====
    {"analyte": "Toluene", "matrix": "Personal Air", "threshold_name": "PEL (8-hr TWA)",
     "regulatory_body": "Cal/OSHA", "value": 10.0, "units": "ppm",
     "threshold_type": "PEL", "jurisdiction": "California",
     "effective_date": "1985-01-01", "source_citation": "Cal/OSHA Title 8 §5155 Table AC-1 (skin)"},
    {"analyte": "Toluene", "matrix": "Personal Air", "threshold_name": "STEL (15-min)",
     "regulatory_body": "Cal/OSHA", "value": 50.0, "units": "ppm",
     "threshold_type": "Ceiling", "jurisdiction": "California",
     "effective_date": "1985-01-01", "source_citation": "Cal/OSHA Title 8 §5155 Table AC-1"},
    {"analyte": "Toluene", "matrix": "Personal Air", "threshold_name": "PEL (8-hr TWA)",
     "regulatory_body": "Fed OSHA", "value": 100.0, "units": "ppm",
     "threshold_type": "PEL", "jurisdiction": "Federal",
     "effective_date": "1971-04-28", "source_citation": "29 CFR 1910.1000 Table Z-1"},

    # ===== XYLENE (mixed isomers) — Cal/OSHA §5155 Table AC-1, Fed OSHA Z-1 =====
    {"analyte": "Xylene", "matrix": "Personal Air", "threshold_name": "PEL (8-hr TWA)",
     "regulatory_body": "Cal/OSHA", "value": 100.0, "units": "ppm",
     "threshold_type": "PEL", "jurisdiction": "California",
     "effective_date": "1985-01-01", "source_citation": "Cal/OSHA Title 8 §5155 Table AC-1"},
    {"analyte": "Xylene", "matrix": "Personal Air", "threshold_name": "STEL (15-min)",
     "regulatory_body": "Cal/OSHA", "value": 150.0, "units": "ppm",
     "threshold_type": "Ceiling", "jurisdiction": "California",
     "effective_date": "1985-01-01", "source_citation": "Cal/OSHA Title 8 §5155 Table AC-1"},
    {"analyte": "Xylene", "matrix": "Personal Air", "threshold_name": "PEL (8-hr TWA)",
     "regulatory_body": "Fed OSHA", "value": 100.0, "units": "ppm",
     "threshold_type": "PEL", "jurisdiction": "Federal",
     "effective_date": "1971-04-28", "source_citation": "29 CFR 1910.1000 Table Z-1"},

    # ===== BENZENE — substance-specific standard, has formal AL =====
    {"analyte": "Benzene", "matrix": "Personal Air", "threshold_name": "PEL (8-hr TWA)",
     "regulatory_body": "Cal/OSHA", "value": 1.0, "units": "ppm",
     "threshold_type": "PEL", "jurisdiction": "California",
     "effective_date": "1987-12-10", "source_citation": "Cal/OSHA Title 8 §5218(c)"},
    {"analyte": "Benzene", "matrix": "Personal Air", "threshold_name": "Action Level (8-hr TWA)",
     "regulatory_body": "Cal/OSHA", "value": 0.5, "units": "ppm",
     "threshold_type": "AL", "jurisdiction": "California",
     "effective_date": "1987-12-10", "source_citation": "Cal/OSHA Title 8 §5218(b)"},
    {"analyte": "Benzene", "matrix": "Personal Air", "threshold_name": "STEL (15-min)",
     "regulatory_body": "Cal/OSHA", "value": 5.0, "units": "ppm",
     "threshold_type": "Ceiling", "jurisdiction": "California",
     "effective_date": "1987-12-10", "source_citation": "Cal/OSHA Title 8 §5218(c)"},
    {"analyte": "Benzene", "matrix": "Personal Air", "threshold_name": "PEL (8-hr TWA)",
     "regulatory_body": "Fed OSHA", "value": 1.0, "units": "ppm",
     "threshold_type": "PEL", "jurisdiction": "Federal",
     "effective_date": "1987-12-10", "source_citation": "29 CFR 1910.1028(c)"},
    {"analyte": "Benzene", "matrix": "Personal Air", "threshold_name": "Action Level (8-hr TWA)",
     "regulatory_body": "Fed OSHA", "value": 0.5, "units": "ppm",
     "threshold_type": "AL", "jurisdiction": "Federal",
     "effective_date": "1987-12-10", "source_citation": "29 CFR 1910.1028(b)"},
    {"analyte": "Benzene", "matrix": "Personal Air", "threshold_name": "STEL (15-min)",
     "regulatory_body": "Fed OSHA", "value": 5.0, "units": "ppm",
     "threshold_type": "Ceiling", "jurisdiction": "Federal",
     "effective_date": "1987-12-10", "source_citation": "29 CFR 1910.1028(c)"},

    # ===== MEK (2-Butanone, Methyl Ethyl Ketone) =====
    {"analyte": "Methyl Ethyl Ketone", "matrix": "Personal Air", "threshold_name": "PEL (8-hr TWA)",
     "regulatory_body": "Cal/OSHA", "value": 200.0, "units": "ppm",
     "threshold_type": "PEL", "jurisdiction": "California",
     "effective_date": "1985-01-01", "source_citation": "Cal/OSHA Title 8 §5155 Table AC-1"},
    {"analyte": "Methyl Ethyl Ketone", "matrix": "Personal Air", "threshold_name": "STEL (15-min)",
     "regulatory_body": "Cal/OSHA", "value": 300.0, "units": "ppm",
     "threshold_type": "Ceiling", "jurisdiction": "California",
     "effective_date": "1985-01-01", "source_citation": "Cal/OSHA Title 8 §5155 Table AC-1"},
    {"analyte": "Methyl Ethyl Ketone", "matrix": "Personal Air", "threshold_name": "PEL (8-hr TWA)",
     "regulatory_body": "Fed OSHA", "value": 200.0, "units": "ppm",
     "threshold_type": "PEL", "jurisdiction": "Federal",
     "effective_date": "1971-04-28", "source_citation": "29 CFR 1910.1000 Table Z-1"},

    # ===== MIBK (4-methyl-2-pentanone, Methyl Isobutyl Ketone) =====
    {"analyte": "Methyl Isobutyl Ketone", "matrix": "Personal Air", "threshold_name": "PEL (8-hr TWA)",
     "regulatory_body": "Cal/OSHA", "value": 50.0, "units": "ppm",
     "threshold_type": "PEL", "jurisdiction": "California",
     "effective_date": "1985-01-01", "source_citation": "Cal/OSHA Title 8 §5155 Table AC-1"},
    {"analyte": "Methyl Isobutyl Ketone", "matrix": "Personal Air", "threshold_name": "STEL (15-min)",
     "regulatory_body": "Cal/OSHA", "value": 75.0, "units": "ppm",
     "threshold_type": "Ceiling", "jurisdiction": "California",
     "effective_date": "1985-01-01", "source_citation": "Cal/OSHA Title 8 §5155 Table AC-1"},
    {"analyte": "Methyl Isobutyl Ketone", "matrix": "Personal Air", "threshold_name": "PEL (8-hr TWA)",
     "regulatory_body": "Fed OSHA", "value": 100.0, "units": "ppm",
     "threshold_type": "PEL", "jurisdiction": "Federal",
     "effective_date": "1971-04-28", "source_citation": "29 CFR 1910.1000 Table Z-1"},

    # ===== METHANOL =====
    {"analyte": "Methanol", "matrix": "Personal Air", "threshold_name": "PEL (8-hr TWA)",
     "regulatory_body": "Cal/OSHA", "value": 200.0, "units": "ppm",
     "threshold_type": "PEL", "jurisdiction": "California",
     "effective_date": "1985-01-01", "source_citation": "Cal/OSHA Title 8 §5155 Table AC-1 (skin)"},
    {"analyte": "Methanol", "matrix": "Personal Air", "threshold_name": "STEL (15-min)",
     "regulatory_body": "Cal/OSHA", "value": 250.0, "units": "ppm",
     "threshold_type": "Ceiling", "jurisdiction": "California",
     "effective_date": "1985-01-01", "source_citation": "Cal/OSHA Title 8 §5155 Table AC-1"},
    {"analyte": "Methanol", "matrix": "Personal Air", "threshold_name": "PEL (8-hr TWA)",
     "regulatory_body": "Fed OSHA", "value": 200.0, "units": "ppm",
     "threshold_type": "PEL", "jurisdiction": "Federal",
     "effective_date": "1971-04-28", "source_citation": "29 CFR 1910.1000 Table Z-1"},

    # ===== ACETONE =====
    {"analyte": "Acetone", "matrix": "Personal Air", "threshold_name": "PEL (8-hr TWA)",
     "regulatory_body": "Cal/OSHA", "value": 500.0, "units": "ppm",
     "threshold_type": "PEL", "jurisdiction": "California",
     "effective_date": "1985-01-01", "source_citation": "Cal/OSHA Title 8 §5155 Table AC-1"},
    {"analyte": "Acetone", "matrix": "Personal Air", "threshold_name": "STEL (15-min)",
     "regulatory_body": "Cal/OSHA", "value": 750.0, "units": "ppm",
     "threshold_type": "Ceiling", "jurisdiction": "California",
     "effective_date": "1985-01-01", "source_citation": "Cal/OSHA Title 8 §5155 Table AC-1"},
    {"analyte": "Acetone", "matrix": "Personal Air", "threshold_name": "PEL (8-hr TWA)",
     "regulatory_body": "Fed OSHA", "value": 1000.0, "units": "ppm",
     "threshold_type": "PEL", "jurisdiction": "Federal",
     "effective_date": "1971-04-28", "source_citation": "29 CFR 1910.1000 Table Z-1"},

    # ===== ISOPROPYL ALCOHOL (IPA, 2-Propanol) =====
    {"analyte": "Isopropyl Alcohol", "matrix": "Personal Air", "threshold_name": "PEL (8-hr TWA)",
     "regulatory_body": "Cal/OSHA", "value": 400.0, "units": "ppm",
     "threshold_type": "PEL", "jurisdiction": "California",
     "effective_date": "1985-01-01", "source_citation": "Cal/OSHA Title 8 §5155 Table AC-1"},
    {"analyte": "Isopropyl Alcohol", "matrix": "Personal Air", "threshold_name": "STEL (15-min)",
     "regulatory_body": "Cal/OSHA", "value": 500.0, "units": "ppm",
     "threshold_type": "Ceiling", "jurisdiction": "California",
     "effective_date": "1985-01-01", "source_citation": "Cal/OSHA Title 8 §5155 Table AC-1"},
    {"analyte": "Isopropyl Alcohol", "matrix": "Personal Air", "threshold_name": "PEL (8-hr TWA)",
     "regulatory_body": "Fed OSHA", "value": 400.0, "units": "ppm",
     "threshold_type": "PEL", "jurisdiction": "Federal",
     "effective_date": "1971-04-28", "source_citation": "29 CFR 1910.1000 Table Z-1"},

    # ===== STODDARD SOLVENT / MINERAL SPIRITS =====
    {"analyte": "Stoddard Solvent", "matrix": "Personal Air", "threshold_name": "PEL (8-hr TWA)",
     "regulatory_body": "Cal/OSHA", "value": 100.0, "units": "ppm",
     "threshold_type": "PEL", "jurisdiction": "California",
     "effective_date": "1985-01-01", "source_citation": "Cal/OSHA Title 8 §5155 Table AC-1"},
    {"analyte": "Stoddard Solvent", "matrix": "Personal Air", "threshold_name": "PEL (8-hr TWA)",
     "regulatory_body": "Fed OSHA", "value": 500.0, "units": "ppm",
     "threshold_type": "PEL", "jurisdiction": "Federal",
     "effective_date": "1971-04-28", "source_citation": "29 CFR 1910.1000 Table Z-1"},
]


def main():
    today_iso = date.today().isoformat()
    created = 0
    skipped = 0

    with app.app_context():
        try:
            for row in TIER2_THRESHOLDS:
                existing = Threshold.query.filter_by(
                    analyte=row["analyte"],
                    matrix=row["matrix"],
                    threshold_name=row["threshold_name"],
                    regulatory_body=row["regulatory_body"],
                ).first()
                if existing is not None:
                    skipped += 1
                    continue

                db.session.add(Threshold(
                    analyte=row["analyte"],
                    matrix=row["matrix"],
                    threshold_name=row["threshold_name"],
                    regulatory_body=row["regulatory_body"],
                    value=row["value"],
                    units=row["units"],
                    threshold_type=row["threshold_type"],
                    jurisdiction=row["jurisdiction"],
                    effective_date=row["effective_date"],
                    superseded_date=None,
                    source_citation=row["source_citation"],
                    last_verified_date=today_iso,
                    active=True,
                ))
                created += 1

            db.session.commit()
        except Exception as exc:
            db.session.rollback()
            print(f"ERROR: {type(exc).__name__}: {exc}")
            raise

        print(f"Created {created}, skipped {skipped} (already existed).")


if __name__ == "__main__":
    main()

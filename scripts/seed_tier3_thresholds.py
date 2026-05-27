import os
import sys
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app
from models import Threshold, db


TIER3_THRESHOLDS = [
    # ===== ISOCYANATES =====
    # TDI (Toluene Diisocyanate) — both isomers, CAS 584-84-9 / 91-08-7
    {"analyte": "Toluene Diisocyanate", "matrix": "Personal Air", "threshold_name": "Ceiling",
     "regulatory_body": "Cal/OSHA", "value": 0.005, "units": "ppm",
     "threshold_type": "Ceiling", "jurisdiction": "California",
     "effective_date": "1985-01-01", "source_citation": "Cal/OSHA Title 8 §5155 Table AC-1"},
    {"analyte": "Toluene Diisocyanate", "matrix": "Personal Air", "threshold_name": "Ceiling",
     "regulatory_body": "Fed OSHA", "value": 0.02, "units": "ppm",
     "threshold_type": "Ceiling", "jurisdiction": "Federal",
     "effective_date": "1971-04-28", "source_citation": "29 CFR 1910.1000 Table Z-1"},

    # MDI (4,4'-Methylenediphenyl Diisocyanate) — CAS 101-68-8
    {"analyte": "Methylene Diphenyl Diisocyanate", "matrix": "Personal Air", "threshold_name": "Ceiling",
     "regulatory_body": "Cal/OSHA", "value": 0.005, "units": "ppm",
     "threshold_type": "Ceiling", "jurisdiction": "California",
     "effective_date": "1985-01-01", "source_citation": "Cal/OSHA Title 8 §5155 Table AC-1"},
    {"analyte": "Methylene Diphenyl Diisocyanate", "matrix": "Personal Air", "threshold_name": "Ceiling",
     "regulatory_body": "Fed OSHA", "value": 0.02, "units": "ppm",
     "threshold_type": "Ceiling", "jurisdiction": "Federal",
     "effective_date": "1971-04-28", "source_citation": "29 CFR 1910.1000 Table Z-1"},

    # HDI (Hexamethylene Diisocyanate) — CAS 822-06-0; Cal/OSHA only (no Fed OSHA PEL)
    {"analyte": "Hexamethylene Diisocyanate", "matrix": "Personal Air", "threshold_name": "Ceiling",
     "regulatory_body": "Cal/OSHA", "value": 0.005, "units": "ppm",
     "threshold_type": "Ceiling", "jurisdiction": "California",
     "effective_date": "1985-01-01", "source_citation": "Cal/OSHA Title 8 §5155 Table AC-1"},

    # ===== NICKEL (Ni) — metal and insoluble compounds, CAS 7440-02-0 =====
    {"analyte": "Nickel", "matrix": "Personal Air", "threshold_name": "PEL (8-hr TWA)",
     "regulatory_body": "Cal/OSHA", "value": 500.0, "units": "µg/m³",
     "threshold_type": "PEL", "jurisdiction": "California",
     "effective_date": "1985-01-01", "source_citation": "Cal/OSHA Title 8 §5155 Table AC-1 (metal & insoluble)"},
    {"analyte": "Nickel", "matrix": "Personal Air", "threshold_name": "PEL (8-hr TWA)",
     "regulatory_body": "Fed OSHA", "value": 1000.0, "units": "µg/m³",
     "threshold_type": "PEL", "jurisdiction": "Federal",
     "effective_date": "1971-04-28", "source_citation": "29 CFR 1910.1000 Table Z-1 (metal & insoluble)"},

    # ===== COPPER (Cu) — dust and mist, CAS 7440-50-8 =====
    {"analyte": "Copper (dust)", "matrix": "Personal Air", "threshold_name": "PEL (8-hr TWA)",
     "regulatory_body": "Cal/OSHA", "value": 1000.0, "units": "µg/m³",
     "threshold_type": "PEL", "jurisdiction": "California",
     "effective_date": "1985-01-01", "source_citation": "Cal/OSHA Title 8 §5155 Table AC-1 (dust & mist)"},
    {"analyte": "Copper (dust)", "matrix": "Personal Air", "threshold_name": "PEL (8-hr TWA)",
     "regulatory_body": "Fed OSHA", "value": 1000.0, "units": "µg/m³",
     "threshold_type": "PEL", "jurisdiction": "Federal",
     "effective_date": "1971-04-28", "source_citation": "29 CFR 1910.1000 Table Z-1 (dust & mist)"},
    {"analyte": "Copper (fume)", "matrix": "Personal Air", "threshold_name": "PEL (8-hr TWA)",
     "regulatory_body": "Cal/OSHA", "value": 100.0, "units": "µg/m³",
     "threshold_type": "PEL", "jurisdiction": "California",
     "effective_date": "1985-01-01", "source_citation": "Cal/OSHA Title 8 §5155 Table AC-1 (fume)"},
    {"analyte": "Copper (fume)", "matrix": "Personal Air", "threshold_name": "PEL (8-hr TWA)",
     "regulatory_body": "Fed OSHA", "value": 100.0, "units": "µg/m³",
     "threshold_type": "PEL", "jurisdiction": "Federal",
     "effective_date": "1971-04-28", "source_citation": "29 CFR 1910.1000 Table Z-1 (fume)"},

    # ===== ZINC OXIDE (ZnO) — fume, CAS 1314-13-2 =====
    {"analyte": "Zinc Oxide", "matrix": "Personal Air", "threshold_name": "PEL (8-hr TWA)",
     "regulatory_body": "Cal/OSHA", "value": 5000.0, "units": "µg/m³",
     "threshold_type": "PEL", "jurisdiction": "California",
     "effective_date": "1985-01-01", "source_citation": "Cal/OSHA Title 8 §5155 Table AC-1 (fume)"},
    {"analyte": "Zinc Oxide", "matrix": "Personal Air", "threshold_name": "STEL (15-min)",
     "regulatory_body": "Cal/OSHA", "value": 10000.0, "units": "µg/m³",
     "threshold_type": "Ceiling", "jurisdiction": "California",
     "effective_date": "1985-01-01", "source_citation": "Cal/OSHA Title 8 §5155 Table AC-1 (fume)"},
    {"analyte": "Zinc Oxide", "matrix": "Personal Air", "threshold_name": "PEL (8-hr TWA)",
     "regulatory_body": "Fed OSHA", "value": 5000.0, "units": "µg/m³",
     "threshold_type": "PEL", "jurisdiction": "Federal",
     "effective_date": "1971-04-28", "source_citation": "29 CFR 1910.1000 Table Z-1 (fume)"},

    # ===== ANTIMONY (Sb) and compounds, CAS 7440-36-0 =====
    {"analyte": "Antimony", "matrix": "Personal Air", "threshold_name": "PEL (8-hr TWA)",
     "regulatory_body": "Cal/OSHA", "value": 500.0, "units": "µg/m³",
     "threshold_type": "PEL", "jurisdiction": "California",
     "effective_date": "1985-01-01", "source_citation": "Cal/OSHA Title 8 §5155 Table AC-1"},
    {"analyte": "Antimony", "matrix": "Personal Air", "threshold_name": "PEL (8-hr TWA)",
     "regulatory_body": "Fed OSHA", "value": 500.0, "units": "µg/m³",
     "threshold_type": "PEL", "jurisdiction": "Federal",
     "effective_date": "1971-04-28", "source_citation": "29 CFR 1910.1000 Table Z-1"},

    # ===== MERCURY (Hg) — vapor and all forms except organic alkyl =====
    {"analyte": "Mercury", "matrix": "Personal Air", "threshold_name": "PEL (8-hr TWA)",
     "regulatory_body": "Cal/OSHA", "value": 25.0, "units": "µg/m³",
     "threshold_type": "PEL", "jurisdiction": "California",
     "effective_date": "1985-01-01", "source_citation": "Cal/OSHA Title 8 §5155 Table AC-1 (vapor, skin)"},
    {"analyte": "Mercury", "matrix": "Personal Air", "threshold_name": "Ceiling",
     "regulatory_body": "Fed OSHA", "value": 100.0, "units": "µg/m³",
     "threshold_type": "Ceiling", "jurisdiction": "Federal",
     "effective_date": "1971-04-28", "source_citation": "29 CFR 1910.1000 Table Z-2 (vapor)"},

    # ===== WELDING FUME, total particulate (not otherwise regulated) =====
    {"analyte": "Welding Fume", "matrix": "Personal Air", "threshold_name": "PEL (8-hr TWA)",
     "regulatory_body": "Cal/OSHA", "value": 5000.0, "units": "µg/m³",
     "threshold_type": "PEL", "jurisdiction": "California",
     "effective_date": "1985-01-01", "source_citation": "Cal/OSHA Title 8 §5155 Table AC-1 (particulate not otherwise regulated)"},
    {"analyte": "Welding Fume", "matrix": "Personal Air", "threshold_name": "PEL (8-hr TWA)",
     "regulatory_body": "Fed OSHA", "value": 5000.0, "units": "µg/m³",
     "threshold_type": "PEL", "jurisdiction": "Federal",
     "effective_date": "1971-04-28", "source_citation": "29 CFR 1910.1000 Table Z-1 (particulate not otherwise regulated)"},
]


def main():
    today_iso = date.today().isoformat()
    created = 0
    skipped = 0

    with app.app_context():
        try:
            for row in TIER3_THRESHOLDS:
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

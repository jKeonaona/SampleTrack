import os
import sys
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app
from models import Threshold, db


TIER1_THRESHOLDS = [
    # ===== BERYLLIUM (Be) — Cal/OSHA Title 8 §1532, Fed OSHA 29 CFR 1926.1124 =====
    {"analyte": "Beryllium", "matrix": "Personal Air", "threshold_name": "PEL (8-hr TWA)",
     "regulatory_body": "Cal/OSHA", "value": 0.2, "units": "µg/m³",
     "threshold_type": "PEL", "jurisdiction": "California",
     "effective_date": "2018-05-11", "source_citation": "Cal/OSHA Title 8 §1532(c)"},
    {"analyte": "Beryllium", "matrix": "Personal Air", "threshold_name": "Action Level (8-hr TWA)",
     "regulatory_body": "Cal/OSHA", "value": 0.1, "units": "µg/m³",
     "threshold_type": "AL", "jurisdiction": "California",
     "effective_date": "2018-05-11", "source_citation": "Cal/OSHA Title 8 §1532(b)"},
    {"analyte": "Beryllium", "matrix": "Personal Air", "threshold_name": "STEL (15-min)",
     "regulatory_body": "Cal/OSHA", "value": 2.0, "units": "µg/m³",
     "threshold_type": "Ceiling", "jurisdiction": "California",
     "effective_date": "2018-05-11", "source_citation": "Cal/OSHA Title 8 §1532(c)"},
    {"analyte": "Beryllium", "matrix": "Personal Air", "threshold_name": "PEL (8-hr TWA)",
     "regulatory_body": "Fed OSHA", "value": 0.2, "units": "µg/m³",
     "threshold_type": "PEL", "jurisdiction": "Federal",
     "effective_date": "2017-05-20", "source_citation": "29 CFR 1926.1124(c)"},
    {"analyte": "Beryllium", "matrix": "Personal Air", "threshold_name": "Action Level (8-hr TWA)",
     "regulatory_body": "Fed OSHA", "value": 0.1, "units": "µg/m³",
     "threshold_type": "AL", "jurisdiction": "Federal",
     "effective_date": "2017-05-20", "source_citation": "29 CFR 1926.1124(b)"},
    {"analyte": "Beryllium", "matrix": "Personal Air", "threshold_name": "STEL (15-min)",
     "regulatory_body": "Fed OSHA", "value": 2.0, "units": "µg/m³",
     "threshold_type": "Ceiling", "jurisdiction": "Federal",
     "effective_date": "2017-05-20", "source_citation": "29 CFR 1926.1124(c)"},

    # ===== CADMIUM (Cd) — Cal/OSHA Title 8 §1532, Fed OSHA 29 CFR 1926.1127 =====
    {"analyte": "Cadmium", "matrix": "Personal Air", "threshold_name": "PEL (8-hr TWA)",
     "regulatory_body": "Cal/OSHA", "value": 5.0, "units": "µg/m³",
     "threshold_type": "PEL", "jurisdiction": "California",
     "effective_date": "1992-12-14", "source_citation": "Cal/OSHA Title 8 §1532(c)"},
    {"analyte": "Cadmium", "matrix": "Personal Air", "threshold_name": "Action Level (8-hr TWA)",
     "regulatory_body": "Cal/OSHA", "value": 2.5, "units": "µg/m³",
     "threshold_type": "AL", "jurisdiction": "California",
     "effective_date": "1992-12-14", "source_citation": "Cal/OSHA Title 8 §1532(b)"},
    {"analyte": "Cadmium", "matrix": "Personal Air", "threshold_name": "PEL (8-hr TWA)",
     "regulatory_body": "Fed OSHA", "value": 5.0, "units": "µg/m³",
     "threshold_type": "PEL", "jurisdiction": "Federal",
     "effective_date": "1992-12-14", "source_citation": "29 CFR 1926.1127(c)"},
    {"analyte": "Cadmium", "matrix": "Personal Air", "threshold_name": "Action Level (8-hr TWA)",
     "regulatory_body": "Fed OSHA", "value": 2.5, "units": "µg/m³",
     "threshold_type": "AL", "jurisdiction": "Federal",
     "effective_date": "1992-12-14", "source_citation": "29 CFR 1926.1127(b)"},

    # ===== TOTAL CHROMIUM (metal and insoluble salts) — Cal/OSHA Table AC-1, Fed OSHA Table Z-1 =====
    {"analyte": "Chromium", "matrix": "Personal Air", "threshold_name": "PEL (8-hr TWA)",
     "regulatory_body": "Cal/OSHA", "value": 500.0, "units": "µg/m³",
     "threshold_type": "PEL", "jurisdiction": "California",
     "effective_date": "1985-01-01", "source_citation": "Cal/OSHA Title 8 §5155 Table AC-1 (Cr metal & insoluble salts)"},
    {"analyte": "Chromium", "matrix": "Personal Air", "threshold_name": "PEL (8-hr TWA)",
     "regulatory_body": "Fed OSHA", "value": 1000.0, "units": "µg/m³",
     "threshold_type": "PEL", "jurisdiction": "Federal",
     "effective_date": "1971-04-28", "source_citation": "29 CFR 1910.1000 Table Z-1 (Cr metal & insoluble salts)"},

    # ===== HEXAVALENT CHROMIUM (Cr VI) — Cal/OSHA Title 8 §1532.2, Fed OSHA 29 CFR 1926.1126 =====
    {"analyte": "Hexavalent Chromium", "matrix": "Personal Air", "threshold_name": "PEL (8-hr TWA)",
     "regulatory_body": "Cal/OSHA", "value": 5.0, "units": "µg/m³",
     "threshold_type": "PEL", "jurisdiction": "California",
     "effective_date": "2008-08-21", "source_citation": "Cal/OSHA Title 8 §1532.2(c)"},
    {"analyte": "Hexavalent Chromium", "matrix": "Personal Air", "threshold_name": "Action Level (8-hr TWA)",
     "regulatory_body": "Cal/OSHA", "value": 2.5, "units": "µg/m³",
     "threshold_type": "AL", "jurisdiction": "California",
     "effective_date": "2008-08-21", "source_citation": "Cal/OSHA Title 8 §1532.2(b)"},
    {"analyte": "Hexavalent Chromium", "matrix": "Personal Air", "threshold_name": "PEL (8-hr TWA)",
     "regulatory_body": "Fed OSHA", "value": 5.0, "units": "µg/m³",
     "threshold_type": "PEL", "jurisdiction": "Federal",
     "effective_date": "2006-05-30", "source_citation": "29 CFR 1926.1126(c)"},
    {"analyte": "Hexavalent Chromium", "matrix": "Personal Air", "threshold_name": "Action Level (8-hr TWA)",
     "regulatory_body": "Fed OSHA", "value": 2.5, "units": "µg/m³",
     "threshold_type": "AL", "jurisdiction": "Federal",
     "effective_date": "2006-05-30", "source_citation": "29 CFR 1926.1126(b)"},

    # ===== ARSENIC (inorganic) — Cal/OSHA Title 8 §1532.3, Fed OSHA 29 CFR 1926.1118 =====
    {"analyte": "Arsenic", "matrix": "Personal Air", "threshold_name": "PEL (8-hr TWA)",
     "regulatory_body": "Cal/OSHA", "value": 10.0, "units": "µg/m³",
     "threshold_type": "PEL", "jurisdiction": "California",
     "effective_date": "1978-05-05", "source_citation": "Cal/OSHA Title 8 §1532.3(c)"},
    {"analyte": "Arsenic", "matrix": "Personal Air", "threshold_name": "Action Level (8-hr TWA)",
     "regulatory_body": "Cal/OSHA", "value": 5.0, "units": "µg/m³",
     "threshold_type": "AL", "jurisdiction": "California",
     "effective_date": "1978-05-05", "source_citation": "Cal/OSHA Title 8 §1532.3(b)"},
    {"analyte": "Arsenic", "matrix": "Personal Air", "threshold_name": "PEL (8-hr TWA)",
     "regulatory_body": "Fed OSHA", "value": 10.0, "units": "µg/m³",
     "threshold_type": "PEL", "jurisdiction": "Federal",
     "effective_date": "1978-05-05", "source_citation": "29 CFR 1926.1118(c)"},
    {"analyte": "Arsenic", "matrix": "Personal Air", "threshold_name": "Action Level (8-hr TWA)",
     "regulatory_body": "Fed OSHA", "value": 5.0, "units": "µg/m³",
     "threshold_type": "AL", "jurisdiction": "Federal",
     "effective_date": "1978-05-05", "source_citation": "29 CFR 1926.1118(b)"},

    # ===== MANGANESE (Mn) — Cal/OSHA Table AC-1, Fed OSHA Table Z-1 =====
    {"analyte": "Manganese", "matrix": "Personal Air", "threshold_name": "PEL (8-hr TWA)",
     "regulatory_body": "Cal/OSHA", "value": 200.0, "units": "µg/m³",
     "threshold_type": "PEL", "jurisdiction": "California",
     "effective_date": "1985-01-01", "source_citation": "Cal/OSHA Title 8 §5155 Table AC-1 (fume)"},
    {"analyte": "Manganese", "matrix": "Personal Air", "threshold_name": "Ceiling",
     "regulatory_body": "Cal/OSHA", "value": 5000.0, "units": "µg/m³",
     "threshold_type": "Ceiling", "jurisdiction": "California",
     "effective_date": "1985-01-01", "source_citation": "Cal/OSHA Title 8 §5155 Table AC-1 (Mn compounds)"},
    {"analyte": "Manganese", "matrix": "Personal Air", "threshold_name": "Ceiling",
     "regulatory_body": "Fed OSHA", "value": 5000.0, "units": "µg/m³",
     "threshold_type": "Ceiling", "jurisdiction": "Federal",
     "effective_date": "1971-04-28", "source_citation": "29 CFR 1910.1000 Table Z-1 (Mn compounds, ceiling only)"},

    # ===== CRYSTALLINE SILICA (Respirable) — Cal/OSHA Title 8 §5204, Fed OSHA 29 CFR 1926.1153 =====
    {"analyte": "Crystalline Silica", "matrix": "Personal Air", "threshold_name": "PEL (8-hr TWA)",
     "regulatory_body": "Cal/OSHA", "value": 50.0, "units": "µg/m³",
     "threshold_type": "PEL", "jurisdiction": "California",
     "effective_date": "2017-09-23", "source_citation": "Cal/OSHA Title 8 §5204(c)"},
    {"analyte": "Crystalline Silica", "matrix": "Personal Air", "threshold_name": "Action Level (8-hr TWA)",
     "regulatory_body": "Cal/OSHA", "value": 25.0, "units": "µg/m³",
     "threshold_type": "AL", "jurisdiction": "California",
     "effective_date": "2017-09-23", "source_citation": "Cal/OSHA Title 8 §5204(b)"},
    {"analyte": "Crystalline Silica", "matrix": "Personal Air", "threshold_name": "PEL (8-hr TWA)",
     "regulatory_body": "Fed OSHA", "value": 50.0, "units": "µg/m³",
     "threshold_type": "PEL", "jurisdiction": "Federal",
     "effective_date": "2017-06-23", "source_citation": "29 CFR 1926.1153(c)"},
    {"analyte": "Crystalline Silica", "matrix": "Personal Air", "threshold_name": "Action Level (8-hr TWA)",
     "regulatory_body": "Fed OSHA", "value": 25.0, "units": "µg/m³",
     "threshold_type": "AL", "jurisdiction": "Federal",
     "effective_date": "2017-06-23", "source_citation": "29 CFR 1926.1153(b)"},

    # ===== ASBESTOS (all forms, PCM) — Cal/OSHA Title 8 §1529, Fed OSHA 29 CFR 1926.1101 =====
    {"analyte": "Asbestos", "matrix": "Personal Air", "threshold_name": "PEL (8-hr TWA)",
     "regulatory_body": "Cal/OSHA", "value": 0.1, "units": "f/cc",
     "threshold_type": "PEL", "jurisdiction": "California",
     "effective_date": "1994-10-11", "source_citation": "Cal/OSHA Title 8 §1529(c)"},
    {"analyte": "Asbestos", "matrix": "Personal Air", "threshold_name": "Action Level (8-hr TWA)",
     "regulatory_body": "Cal/OSHA", "value": 0.1, "units": "f/cc",
     "threshold_type": "AL", "jurisdiction": "California",
     "effective_date": "1994-10-11", "source_citation": "Cal/OSHA Title 8 §1529(b)"},
    {"analyte": "Asbestos", "matrix": "Personal Air", "threshold_name": "Excursion Limit (30-min)",
     "regulatory_body": "Cal/OSHA", "value": 1.0, "units": "f/cc",
     "threshold_type": "Ceiling", "jurisdiction": "California",
     "effective_date": "1994-10-11", "source_citation": "Cal/OSHA Title 8 §1529(c)"},
    {"analyte": "Asbestos", "matrix": "Personal Air", "threshold_name": "PEL (8-hr TWA)",
     "regulatory_body": "Fed OSHA", "value": 0.1, "units": "f/cc",
     "threshold_type": "PEL", "jurisdiction": "Federal",
     "effective_date": "1994-10-11", "source_citation": "29 CFR 1926.1101(c)"},
    {"analyte": "Asbestos", "matrix": "Personal Air", "threshold_name": "Action Level (8-hr TWA)",
     "regulatory_body": "Fed OSHA", "value": 0.1, "units": "f/cc",
     "threshold_type": "AL", "jurisdiction": "Federal",
     "effective_date": "1994-10-11", "source_citation": "29 CFR 1926.1101(b)"},
    {"analyte": "Asbestos", "matrix": "Personal Air", "threshold_name": "Excursion Limit (30-min)",
     "regulatory_body": "Fed OSHA", "value": 1.0, "units": "f/cc",
     "threshold_type": "Ceiling", "jurisdiction": "Federal",
     "effective_date": "1994-10-11", "source_citation": "29 CFR 1926.1101(c)"},

    # ===== COAL TAR PITCH VOLATILES (CTPV, benzene-soluble fraction) =====
    {"analyte": "Coal Tar Pitch Volatiles", "matrix": "Personal Air", "threshold_name": "PEL (8-hr TWA)",
     "regulatory_body": "Cal/OSHA", "value": 200.0, "units": "µg/m³",
     "threshold_type": "PEL", "jurisdiction": "California",
     "effective_date": "1985-01-01", "source_citation": "Cal/OSHA Title 8 §5155 Table AC-1 (benzene-soluble fraction)"},
    {"analyte": "Coal Tar Pitch Volatiles", "matrix": "Personal Air", "threshold_name": "PEL (8-hr TWA)",
     "regulatory_body": "Fed OSHA", "value": 200.0, "units": "µg/m³",
     "threshold_type": "PEL", "jurisdiction": "Federal",
     "effective_date": "1971-04-28", "source_citation": "29 CFR 1910.1000 Table Z-1 (benzene-soluble fraction)"},
]


def main():
    today_iso = date.today().isoformat()
    created = 0
    skipped = 0

    with app.app_context():
        try:
            for row in TIER1_THRESHOLDS:
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

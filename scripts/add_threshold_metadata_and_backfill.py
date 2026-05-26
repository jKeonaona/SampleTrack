import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import inspect, text

from app import app
from models import Threshold, db


COLUMNS = [
    ("jurisdiction", "VARCHAR(20) NOT NULL DEFAULT 'Both'"),
    ("threshold_type", "VARCHAR(20) NOT NULL DEFAULT 'PEL'"),
]


def _classify(name, body):
    """Return (jurisdiction, threshold_type) inferred from name + regulatory_body.

    Matches against the concatenated 'name | body' string, case-insensitive.
    """
    haystack = f"{name or ''} | {body or ''}".lower()

    def has(*needles):
        return any(n.lower() in haystack for n in needles)

    if has("Cal/OSHA", "Cal-OSHA", "Cal OSHA"):
        return "California", _osha_subtype(haystack)
    if has("Fed OSHA", "Federal OSHA"):
        return "Federal", _osha_subtype(haystack)
    if has("OSHA") and not has("Cal"):
        return "Federal", _osha_subtype(haystack)

    if has("EPA NAAQS", "NAAQS"):
        return "Both", "Ambient"
    if has("CARB", "CAAQS"):
        return "California", "Ambient"
    if has("BAAQMD"):
        return "California", "Ambient"
    if has("SCAQMD"):
        return "California", "Ambient"

    if has("HUD"):
        return "Both", "Clearance"
    if has("CHHSL"):
        return "California", "Clearance"
    if has("Lead-Based Paint", "LBP"):
        return "Both", "Clearance"

    return None, None


def _osha_subtype(haystack_lower):
    if "action level" in haystack_lower or " al " in haystack_lower or haystack_lower.endswith(" al"):
        return "AL"
    if "ceiling" in haystack_lower:
        return "Ceiling"
    return "PEL"


def main():
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
        totals = {
            "California": 0, "Federal": 0, "Both": 0,
            "PEL": 0, "AL": 0, "Ceiling": 0, "Ambient": 0, "Clearance": 0,
        }
        unmatched = 0

        for t in thresholds:
            jurisdiction, ttype = _classify(t.threshold_name, t.regulatory_body)
            if jurisdiction is None:
                print(f"  ! unmatched: {t.analyte} / {t.matrix} / {t.threshold_name} / {t.regulatory_body}")
                unmatched += 1
                jurisdiction, ttype = "Both", "PEL"
            t.jurisdiction = jurisdiction
            t.threshold_type = ttype
            totals[jurisdiction] += 1
            totals[ttype] += 1

        db.session.commit()

        print(
            f"Updated {len(thresholds)} thresholds: "
            f"{totals['California']} California, {totals['Federal']} Federal, "
            f"{totals['Both']} Both. "
            f"Types: {totals['PEL']} PELs, {totals['AL']} ALs, "
            f"{totals['Ceiling']} Ceilings, {totals['Ambient']} Ambient, "
            f"{totals['Clearance']} Clearance."
        )
        if unmatched:
            print(f"WARNING: {unmatched} threshold(s) unmatched — left at defaults (Both / PEL).")


if __name__ == "__main__":
    main()

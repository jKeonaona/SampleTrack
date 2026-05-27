import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import inspect, text

from app import app
from models import db


# (column_name, column_type)
# 'status' already exists in the Project model with default "active"; we only
# add it here if a fresh DB ever lacks it.
COLUMNS = [
    ("status", "VARCHAR(20) NOT NULL DEFAULT 'active'"),
    ("archived_at", "DATETIME"),
]


def main():
    added = 0
    with app.app_context():
        inspector = inspect(db.engine)
        existing = {col["name"] for col in inspector.get_columns("project")}
        for name, col_type in COLUMNS:
            if name in existing:
                print(f"Skipped (already exists): {name}")
                continue
            db.session.execute(text(f"ALTER TABLE project ADD COLUMN {name} {col_type}"))
            db.session.commit()
            print(f"Added column: {name}")
            added += 1

        if "status" not in existing:
            backfilled = db.session.execute(text(
                "UPDATE project SET status = 'active' WHERE status IS NULL OR status = ''"
            )).rowcount or 0
            db.session.commit()
            print(f"Backfilled {backfilled} rows to status='active'.")

    if added == 0:
        print("No migration needed.")


if __name__ == "__main__":
    main()

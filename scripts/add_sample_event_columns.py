import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import inspect, text

from app import app
from models import db


COLUMNS = [
    ("sampling_event_id", "INTEGER"),
    ("is_blank", "BOOLEAN DEFAULT 0 NOT NULL"),
    ("sequence_number", "INTEGER"),
    ("matrix_code", "VARCHAR(10)"),
]


def main():
    added = 0
    with app.app_context():
        inspector = inspect(db.engine)
        existing = {col["name"] for col in inspector.get_columns("sample")}
        for name, col_type in COLUMNS:
            if name in existing:
                print(f"Skipped (already exists): {name}")
                continue
            db.session.execute(text(f"ALTER TABLE sample ADD COLUMN {name} {col_type}"))
            db.session.commit()
            print(f"Added column: {name}")
            added += 1

    if added == 0:
        print("No migration needed.")


if __name__ == "__main__":
    main()

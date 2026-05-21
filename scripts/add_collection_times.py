import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from sqlalchemy.exc import OperationalError

from app import app
from models import db


COLUMNS = [
    ("collection_start_time", "VARCHAR(20)"),
]


def main():
    added = 0
    with app.app_context():
        for name, col_type in COLUMNS:
            try:
                db.session.execute(text(f"ALTER TABLE sample ADD COLUMN {name} {col_type}"))
                db.session.commit()
                print(f"Added column: {name}")
                added += 1
            except OperationalError as exc:
                if "duplicate column name" in str(exc).lower():
                    db.session.rollback()
                    print(f"Skipped (already exists): {name}")
                else:
                    raise

    if added == 0:
        print("No migration needed.")


if __name__ == "__main__":
    main()

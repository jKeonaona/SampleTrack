import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from sqlalchemy.exc import OperationalError

from app import app
from models import db


COLUMNS = [
    ("employee_name", "VARCHAR(200)"),
    ("work_area", "VARCHAR(200)"),
    ("task_description", "VARCHAR(200)"),
]

DATA_MIGRATIONS = [
    ("employee_name", "UPDATE sample SET employee_name = employee_monitored WHERE employee_name IS NULL AND employee_monitored IS NOT NULL"),
    ("task_description", "UPDATE sample SET task_description = employee_task WHERE task_description IS NULL AND employee_task IS NOT NULL"),
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
                msg = str(exc).lower()
                if "duplicate column name" in msg:
                    db.session.rollback()
                    print(f"Skipped (already exists): {name}")
                else:
                    raise

        for field, sql in DATA_MIGRATIONS:
            try:
                result = db.session.execute(text(sql))
                db.session.commit()
                rowcount = result.rowcount if result.rowcount is not None else 0
                if rowcount > 0:
                    print(f"Migrated {rowcount} rows: {field}")
                else:
                    print(f"No data to migrate: {field}")
            except OperationalError as exc:
                db.session.rollback()
                print(f"Skipped data migration for {field}: {exc}")

    if added == 0:
        print("No schema migration needed.")


if __name__ == "__main__":
    main()

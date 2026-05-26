import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import inspect, text

from app import app
from models import db


def main():
    with app.app_context():
        inspector = inspect(db.engine)
        existing = {col["name"] for col in inspector.get_columns("project")}
        if "jurisdiction" in existing:
            print("Skipped (already exists): jurisdiction")
            return

        db.session.execute(text(
            "ALTER TABLE project ADD COLUMN jurisdiction VARCHAR(20) NOT NULL DEFAULT 'California'"
        ))
        db.session.commit()
        print("Added column: jurisdiction (default 'California')")

        backfilled = db.session.execute(text(
            "UPDATE project SET jurisdiction = 'California' WHERE jurisdiction IS NULL OR jurisdiction = ''"
        )).rowcount or 0
        db.session.commit()
        print(f"Backfilled {backfilled} existing project rows to 'California'.")


if __name__ == "__main__":
    main()

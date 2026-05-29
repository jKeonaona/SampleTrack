import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text

from app import app
from models import db


def main():
    with app.app_context():
        rows = db.session.execute(text("PRAGMA table_info(field_sample_record)")).fetchall()
        existing = {row[1] for row in rows}
        if "area_type" in existing:
            print("OK: area_type already present")
            return
        db.session.execute(text("ALTER TABLE field_sample_record ADD COLUMN area_type VARCHAR(50)"))
        db.session.commit()
        print("OK: area_type added")


if __name__ == "__main__":
    main()

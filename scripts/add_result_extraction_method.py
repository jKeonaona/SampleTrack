import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text

from app import app
from models import db


def main():
    with app.app_context():
        rows = db.session.execute(text("PRAGMA table_info(result)")).fetchall()
        existing = {row[1] for row in rows}
        if "extraction_method" in existing:
            print("OK: column already present")
            return
        db.session.execute(text("ALTER TABLE result ADD COLUMN extraction_method VARCHAR(50)"))
        db.session.commit()
        print("OK: added extraction_method column")


if __name__ == "__main__":
    main()

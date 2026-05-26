import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import inspect

from app import app
from models import SamplingEvent, db


def main():
    with app.app_context():
        inspector = inspect(db.engine)
        if inspector.has_table(SamplingEvent.__tablename__):
            print("Table already exists; skipping.")
            return
        SamplingEvent.__table__.create(bind=db.engine)
        print(f"Created table: {SamplingEvent.__tablename__}")


if __name__ == "__main__":
    main()

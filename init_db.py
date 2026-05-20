import os

from app import app
from models import db


def main():
    with app.app_context():
        db.create_all()
        db_uri = app.config["SQLALCHEMY_DATABASE_URI"]
        if db_uri.startswith("sqlite:///"):
            relative_path = db_uri.replace("sqlite:///", "", 1)
            db_path = os.path.join(app.instance_path, relative_path)
        else:
            db_path = db_uri
        print(f"Database initialized at: {db_path}")


if __name__ == "__main__":
    main()

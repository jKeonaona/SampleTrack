import getpass
import sys

from app import app
from models import db, User


def main():
    if len(sys.argv) < 2:
        print("Usage: python create_admin.py <email>")
        sys.exit(1)

    email = sys.argv[1].strip().lower()
    if not email:
        print("Email cannot be empty.")
        sys.exit(1)

    password = getpass.getpass("Password: ")
    confirm = getpass.getpass("Confirm password: ")
    if password != confirm:
        print("Passwords do not match.")
        sys.exit(1)
    if not password:
        print("Password cannot be empty.")
        sys.exit(1)

    with app.app_context():
        existing = User.query.filter_by(email=email).first()
        if existing is not None:
            print(f"User {email} already exists.")
            sys.exit(1)

        user = User(email=email, role="admin", name="Admin", active=True)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

    print(f"Admin user {email} created")


if __name__ == "__main__":
    main()

from datetime import datetime

from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import current_user, login_required, login_user, logout_user

from models import db, User

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/login", methods=["GET"])
def login():
    if current_user.is_authenticated:
        return redirect("/")
    return render_template("auth/login.html", email="")


@auth_bp.route("/login", methods=["POST"])
def login_post():
    email = (request.form.get("email") or "").strip().lower()
    password = request.form.get("password") or ""

    user = User.query.filter_by(email=email).first()
    if user is None or not user.is_active or not user.check_password(password):
        flash("Invalid email or password.", "error")
        return render_template("auth/login.html", email=email), 401

    login_user(user)
    user.last_login = datetime.utcnow()
    db.session.commit()

    next_url = request.args.get("next") or "/"
    return redirect(next_url)


@auth_bp.route("/logout", methods=["GET"])
@login_required
def logout():
    logout_user()
    return redirect(url_for("auth.login"))

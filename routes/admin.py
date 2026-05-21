from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import current_user

from models import db, User
from routes._helpers import admin_required

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")

VALID_ROLES = ("admin", "user")
MIN_PASSWORD_LENGTH = 8


@admin_bp.route("/", methods=["GET"])
@admin_required
def dashboard():
    return render_template(
        "admin/dashboard.html",
        total_users=User.query.count(),
        active_users=User.query.filter_by(active=True).count(),
        admin_count=User.query.filter_by(role="admin").count(),
    )


@admin_bp.route("/users", methods=["GET"])
@admin_required
def users_list():
    users = User.query.order_by(User.created_at.desc()).all()
    return render_template("admin/users_list.html", users=users)


@admin_bp.route("/users/new", methods=["GET"])
@admin_required
def user_new():
    return render_template(
        "admin/user_form.html",
        mode="new",
        user=None,
        form={"email": "", "name": "", "role": "user"},
    )


@admin_bp.route("/users", methods=["POST"])
@admin_required
def user_create():
    form = {
        "email": (request.form.get("email") or "").strip().lower(),
        "name": (request.form.get("name") or "").strip(),
        "role": (request.form.get("role") or "user").strip(),
    }
    password = request.form.get("password") or ""
    password_confirm = request.form.get("password_confirm") or ""

    error = _validate_new_user(form, password, password_confirm)
    if error:
        flash(error, "error")
        return render_template("admin/user_form.html", mode="new", user=None, form=form), 400

    user = User(
        email=form["email"],
        name=form["name"] or None,
        role=form["role"],
        active=True,
    )
    user.set_password(password)
    db.session.add(user)
    db.session.commit()

    flash(f"User {user.email} created.", "success")
    return redirect(url_for("admin.users_list"))


@admin_bp.route("/users/<int:user_id>", methods=["GET"])
@admin_required
def user_edit(user_id):
    user = User.query.get_or_404(user_id)
    form = {
        "email": user.email,
        "name": user.name or "",
        "role": user.role or "user",
        "active": bool(user.active),
    }
    return render_template("admin/user_form.html", mode="edit", user=user, form=form)


@admin_bp.route("/users/<int:user_id>", methods=["POST"])
@admin_required
def user_update(user_id):
    user = User.query.get_or_404(user_id)

    form = {
        "email": (request.form.get("email") or "").strip().lower(),
        "name": (request.form.get("name") or "").strip(),
        "role": (request.form.get("role") or "user").strip(),
        "active": request.form.get("active") == "on",
    }

    if not form["email"]:
        flash("Email is required.", "error")
        return render_template("admin/user_form.html", mode="edit", user=user, form=form), 400
    if form["role"] not in VALID_ROLES:
        flash(f"Role must be one of: {', '.join(VALID_ROLES)}.", "error")
        return render_template("admin/user_form.html", mode="edit", user=user, form=form), 400
    if form["email"] != user.email:
        clash = User.query.filter_by(email=form["email"]).first()
        if clash is not None and clash.id != user.id:
            flash(f"Email '{form['email']}' is already in use.", "error")
            return render_template("admin/user_form.html", mode="edit", user=user, form=form), 400

    if user.id == current_user.id and not form["active"]:
        flash("You cannot deactivate yourself.", "error")
        return render_template("admin/user_form.html", mode="edit", user=user, form=form), 400
    if user.id == current_user.id and form["role"] != "admin":
        flash("You cannot demote yourself from admin.", "error")
        return render_template("admin/user_form.html", mode="edit", user=user, form=form), 400

    user.email = form["email"]
    user.name = form["name"] or None
    user.role = form["role"]
    user.active = form["active"]
    db.session.commit()

    flash("User updated.", "success")
    return redirect(url_for("admin.users_list"))


@admin_bp.route("/users/<int:user_id>/password", methods=["POST"])
@admin_required
def user_password_reset(user_id):
    user = User.query.get_or_404(user_id)

    password = request.form.get("password") or ""
    password_confirm = request.form.get("password_confirm") or ""

    if len(password) < MIN_PASSWORD_LENGTH:
        flash(f"Password must be at least {MIN_PASSWORD_LENGTH} characters.", "error")
        return redirect(url_for("admin.user_edit", user_id=user.id))
    if password != password_confirm:
        flash("Passwords do not match.", "error")
        return redirect(url_for("admin.user_edit", user_id=user.id))

    user.set_password(password)
    db.session.commit()

    flash(f"Password reset for {user.email}.", "success")
    return redirect(url_for("admin.user_edit", user_id=user.id))


@admin_bp.route("/users/<int:user_id>/deactivate", methods=["POST"])
@admin_required
def user_deactivate(user_id):
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash("You cannot deactivate yourself.", "error")
        return redirect(url_for("admin.users_list"))

    user.active = False
    db.session.commit()
    flash(f"User {user.email} deactivated.", "success")
    return redirect(url_for("admin.users_list"))


@admin_bp.route("/users/<int:user_id>/activate", methods=["POST"])
@admin_required
def user_activate(user_id):
    user = User.query.get_or_404(user_id)
    user.active = True
    db.session.commit()
    flash(f"User {user.email} activated.", "success")
    return redirect(url_for("admin.users_list"))


def _validate_new_user(form, password, password_confirm):
    if not form["email"]:
        return "Email is required."
    if form["role"] not in VALID_ROLES:
        return f"Role must be one of: {', '.join(VALID_ROLES)}."
    if len(password) < MIN_PASSWORD_LENGTH:
        return f"Password must be at least {MIN_PASSWORD_LENGTH} characters."
    if password != password_confirm:
        return "Passwords do not match."
    existing = User.query.filter_by(email=form["email"]).first()
    if existing is not None:
        return f"Email '{form['email']}' is already in use."
    return None

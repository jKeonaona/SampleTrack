from flask import Blueprint, render_template, request, redirect, url_for, flash

from models import db, Project

projects_bp = Blueprint("projects", __name__, url_prefix="/projects")


@projects_bp.route("/", methods=["GET"])
def list_projects():
    projects = Project.query.order_by(Project.created_at.desc()).all()
    return render_template("projects/list.html", projects=projects)


@projects_bp.route("/new", methods=["GET"])
def new():
    return render_template("projects/new.html", form={})


@projects_bp.route("/", methods=["POST"])
def create():
    form = {
        "project_number": (request.form.get("project_number") or "").strip(),
        "name": (request.form.get("name") or "").strip(),
        "client": (request.form.get("client") or "").strip(),
        "location": (request.form.get("location") or "").strip(),
        "status": (request.form.get("status") or "active").strip(),
    }

    if not form["project_number"]:
        flash("Project number is required.", "error")
        return render_template("projects/new.html", form=form), 400
    if not form["name"]:
        flash("Name is required.", "error")
        return render_template("projects/new.html", form=form), 400

    existing = Project.query.filter_by(project_number=form["project_number"]).first()
    if existing is not None:
        flash(f"Project number '{form['project_number']}' already exists.", "error")
        return render_template("projects/new.html", form=form), 400

    project = Project(
        project_number=form["project_number"],
        name=form["name"],
        client=form["client"] or None,
        location=form["location"] or None,
        status=form["status"] or "active",
    )
    db.session.add(project)
    db.session.commit()

    flash(f"Project '{project.project_number}' created.", "success")
    return redirect(url_for("projects.detail", project_id=project.id))


@projects_bp.route("/<int:project_id>", methods=["GET"])
def detail(project_id):
    project = Project.query.get_or_404(project_id)
    return render_template("projects/detail.html", project=project, samples=project.samples)

from flask import Flask, render_template, jsonify
from flask_login import LoginManager, current_user, login_required
from dotenv import load_dotenv
import os

from models import db, Project, Sample, Result, User
from routes.projects import projects_bp
from routes.uploads import uploads_bp
from routes.auth import auth_bp

load_dotenv()

app = Flask(__name__, instance_relative_config=True)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///sampletrack.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-only-change-in-prod")

db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "auth.login"


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


app.register_blueprint(projects_bp)
app.register_blueprint(uploads_bp)
app.register_blueprint(auth_bp)


@app.route("/")
@login_required
def index():
    return render_template(
        "index.html",
        project_count=Project.query.count(),
        sample_count=Sample.query.count(),
        result_count=Result.query.count(),
    )


@app.route("/health")
def health():
    return jsonify({"status": "ok", "app": "SampleTrack"})


if __name__ == "__main__":
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "6000"))
    debug = os.getenv("FLASK_ENV", "").lower() == "development"
    app.run(host=host, port=port, debug=debug)

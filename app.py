from flask import Flask, render_template, jsonify
from dotenv import load_dotenv
import os

load_dotenv()

app = Flask(__name__, instance_relative_config=True)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/health")
def health():
    return jsonify({"status": "ok", "app": "SampleTrack"})


if __name__ == "__main__":
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "6000"))
    debug = os.getenv("FLASK_ENV", "").lower() == "development"
    app.run(host=host, port=port, debug=debug)

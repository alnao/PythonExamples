from flask import Flask, jsonify, request

from .tasks import long_task


def create_app() -> Flask:
    app = Flask(__name__)

    @app.route("/")
    def index() -> str:
        return "Flask + Celery + Redis example is running"

    @app.route("/enqueue", methods=["POST"])
    def enqueue():
        payload = request.get_json(silent=True) or {}
        duration = int(payload.get("duration", 5))
        task = long_task.delay(duration)
        return jsonify({"task_id": task.id}), 202

    @app.route("/result/<task_id>")
    def result(task_id: str):
        task = long_task.AsyncResult(task_id)
        if task.state == "PENDING":
            return jsonify({"state": task.state}), 200
        if task.state == "FAILURE":
            return jsonify({"state": task.state, "error": str(task.result)}), 500
        return jsonify({"state": task.state, "result": task.result}), 200

    return app


app = create_app()



"""Agent Zero Web Dashboard — real-time GUI for the 3-agent system + SaaS monetization."""

import os
import sys
import time
import json
import queue
import threading
import subprocess
from pathlib import Path
from datetime import datetime
from flask import Flask, render_template, Response, jsonify, request, abort
from core.audit_logger import audit
from core.socket_manager import init_socketio, socketio

BASE_DIR = Path(__file__).resolve().parent.parent
LOG_DIR = BASE_DIR / "logs"

app = Flask(__name__)
init_socketio(app)

# API Key Authentication Middleware
API_KEY = os.getenv('ANGETIC_ESSENCE_API_KEY', 'default-secret-change-me')

@app.before_request
def check_api_key():
    # Skip authentication for static files, health check, and root
    if request.endpoint == 'static' or request.path in ['/health', '/']:
        return
    # Check for API key in header
    provided_key = request.headers.get('X-API-Key')
    if provided_key != API_KEY:
        abort(401, description='Invalid or missing API key')

agent_process: subprocess.Popen | None = None
process_lock = threading.Lock()
log_queue: queue.Queue = queue.Queue()
agent_status = {
    "developer": {"status": "idle", "last_action": "", "uptime": 0},
    "tester": {"status": "idle", "last_action": "", "uptime": 0},
    "critic": {"status": "idle", "last_action": "", "uptime": 0},
    "optimizer": {"status": "idle", "last_action": "", "uptime": 0},
}
current_iteration = 0
start_time = 0
revenue_data = {
    "total_revenue": 0,
    "active_subscribers": 0,
    "transactions_today": 0,
    "stripe_configured": False,
    "products": [],
    "opportunities_found": 0,
    "last_scrape": None,
}


def tail_logs():
    last_sizes = {}
    while True:
        for log_file in LOG_DIR.glob("*.log"):
            try:
                size = log_file.stat().st_size
                if log_file.name not in last_sizes:
                    last_sizes[log_file.name] = size
                    continue
                if size > last_sizes[log_file.name]:
                    with open(log_file, "r", encoding="utf-8") as f:
                        f.seek(last_sizes[log_file.name])
                        for line in f:
                            line = line.strip()
                            if line:
                                log_queue.put(line)
                                _parse_log_line(line, log_file.name)
                    last_sizes[log_file.name] = size
            except Exception:
                pass
        time.sleep(1)


def _parse_log_line(line: str, source: str):
    global current_iteration
    agent_name = source.replace(".log", "")
    if agent_name in agent_status:
        agent_status[agent_name]["last_action"] = line[-120:]
        agent_status[agent_name]["status"] = "running"

    if "Iteration" in line and "/" in line:
        try:
            parts = line.split("Iteration")[1].split("/")
            current_iteration = int(parts[0].strip())
        except Exception:
            pass


def stream_output():
    global agent_process
    while True:
        if agent_process and agent_process.stdout:
            line = agent_process.stdout.readline()
            if line:
                log_queue.put(line.strip())
        time.sleep(0.1)


@app.route("/")
def index():
    return render_template("dashboard.html")


@app.route("/api/status")
def get_status():
    global current_iteration, start_time
    uptime = time.time() - start_time if start_time else 0
    return jsonify(
        {
            "agents": agent_status,
            "iteration": current_iteration,
            "running": agent_process is not None and agent_process.poll() is None,
            "uptime": round(uptime, 1),
        }
    )


@app.route("/api/start", methods=["POST"])
def start_agents():
    global agent_process, start_time
    with process_lock:
        if agent_process and agent_process.poll() is None:
            return jsonify({"error": "Already running"}), 400
        for name in agent_status:
            agent_status[name]["status"] = "running"
            agent_status[name]["last_action"] = "Initializing..."
        start_time = time.time()
        agent_process = subprocess.Popen(
            [sys.executable, str(BASE_DIR / "main.py")],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            cwd=str(BASE_DIR),
        )
        threading.Thread(target=stream_output, daemon=True).start()
    return jsonify({"status": "started"})


@app.route("/api/stop", methods=["POST"])
def stop_agents():
    global agent_process
    with process_lock:
        if agent_process and agent_process.poll() is None:
            agent_process.terminate()
            try:
                agent_process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                agent_process.kill()
            for name in agent_status:
                agent_status[name]["status"] = "idle"
                agent_status[name]["last_action"] = "Stopped."
            agent_process = None
    return jsonify({"status": "stopped"})


@app.route("/api/monetization")
def get_monetization():
    global revenue_data
    stripe_key = os.environ.get("STRIPE_SECRET_KEY", "")
    revenue_data["stripe_configured"] = bool(stripe_key)
    return jsonify(revenue_data)


@app.route("/api/logs")
def stream_logs():
    def generate():
        seen = set()
        while True:
            try:
                line = log_queue.get(timeout=1)
                if line and line not in seen:
                    seen.add(line)
                    if len(seen) > 500:
                        seen.clear()
                    yield f"data: {json.dumps({'text': line})}\n\n"
            except queue.Empty:
                yield f"data: {json.dumps({'text': ''})}\n\n"

    return Response(generate(), mimetype="text/event-stream")


if __name__ == "__main__":
    LOG_DIR.mkdir(exist_ok=True)
    threading.Thread(target=tail_logs, daemon=True).start()
    socketio.run(app, host="127.0.0.1", port=5000, debug=False, allow_unsafe_werkzeug=True)

"""
ML Routes — expose the leak detection model via REST.
"""

from flask import Blueprint, jsonify, request
from models.leak_detector import predict as leak_predict
from services.water_service import get_latest_reading, insert_leak_log, get_recent_leak_logs

ml_bp = Blueprint("ml", __name__)


@ml_bp.route("/leak-status", methods=["GET"])
def leak_status():
    """Run leak inference on the latest sensor reading."""
    reading = get_latest_reading()

    if not reading:
        return jsonify({"error": "No sensor data available yet."}), 404

    result = leak_predict(reading["flow_rate"], reading["tank_level"])

    # Persist to leak_logs
    insert_leak_log(result["status"], result["confidence"])

    result["flow_rate"]  = reading["flow_rate"]
    result["tank_level"] = reading["tank_level"]
    result["timestamp"]  = reading["timestamp"]

    return jsonify(result)


@ml_bp.route("/leak-history", methods=["GET"])
def leak_history():
    """Return recent leak log entries."""
    limit = int(request.args.get("limit", 20))
    logs  = get_recent_leak_logs(limit=limit)
    return jsonify(logs)

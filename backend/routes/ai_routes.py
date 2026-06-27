"""
AI Routes — Gemini-powered insight and daily report generation.
"""

from flask import Blueprint, jsonify
from services.water_service import (
    get_latest_reading, get_daily_report_data, get_readings_last_24h
)
from services.cost_service  import calculate_dynamic_cost, calculate_conservation_score
from services.ai_service    import generate_water_insight, generate_daily_report
from models.leak_detector   import predict as leak_predict

ai_bp = Blueprint("ai", __name__)


@ai_bp.route("/generate-insight", methods=["POST"])
def generate_insight():
    """Generate a real-time AI water insight using the latest sensor data."""
    reading = get_latest_reading()
    if not reading:
        return jsonify({"error": "No sensor data available yet."}), 404

    flow_rate  = reading["flow_rate"]
    tank_level = reading["tank_level"]

    leak         = leak_predict(flow_rate, tank_level)
    cost         = calculate_dynamic_cost(flow_rate, tank_level,
                                          leak["status"] == "Leak")
    conservation = calculate_conservation_score(flow_rate, tank_level, leak["status"])

    result = generate_water_insight(
        flow_rate, tank_level,
        leak["status"],
        conservation["score"],
        cost
    )
    return jsonify(result)


@ai_bp.route("/generate-report", methods=["POST"])
def generate_report():
    """Generate a structured daily summary report."""
    daily     = get_daily_report_data()
    all_data  = get_readings_last_24h()

    reading = get_latest_reading()
    score   = 50   # default
    if reading:
        leak = leak_predict(reading["flow_rate"], reading["tank_level"])
        cons = calculate_conservation_score(
            reading["flow_rate"], reading["tank_level"], leak["status"]
        )
        score = cons["score"]

    result = generate_daily_report(
        avg_flow          = daily["avg_flow"],
        peak_hour         = daily["peak_hour"],
        leak_incidents    = daily["leak_incidents"],
        conservation_score= score,
        daily_data        = all_data
    )
    return jsonify(result)

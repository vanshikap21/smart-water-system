"""
Data Routes — endpoints for sensor readings, analytics, cost, and conservation.
"""

from flask import Blueprint, jsonify, request
from services.water_service import (
    get_latest_reading, get_recent_readings,
    get_hourly_consumption, get_daily_consumption,
    get_tank_level_trend, get_cost_trend
)
from services.cost_service import (
    calculate_dynamic_cost,
    calculate_conservation_score,
    calculate_savings
)
from models.leak_detector import predict as leak_predict
from services.water_service import insert_cost_log

data_bp = Blueprint("data", __name__)


# ---------------------------------------------------------------------------
# GET /api/live-data
# ---------------------------------------------------------------------------

@data_bp.route("/live-data", methods=["GET"])
def live_data():
    """Return the latest sensor reading with derived metrics."""
    reading = get_latest_reading()

    if not reading:
        return jsonify({"error": "No data available yet."}), 404

    flow_rate  = reading["flow_rate"]
    tank_level = reading["tank_level"]

    # Leak status
    leak = leak_predict(flow_rate, tank_level)

    # Cost
    cost = calculate_dynamic_cost(flow_rate, tank_level,
                                   leak_detected=(leak["status"] == "Leak"))
    insert_cost_log(cost["estimated_cost"])

    # Conservation score
    conservation = calculate_conservation_score(
        flow_rate, tank_level, leak["status"]
    )

    return jsonify({
        "timestamp":          reading["timestamp"],
        "flow_rate":          flow_rate,
        "tank_level":         tank_level,
        "leak":               leak,
        "cost":               cost,
        "conservation":       conservation
    })


# ---------------------------------------------------------------------------
# GET /api/analytics
# ---------------------------------------------------------------------------

@data_bp.route("/analytics", methods=["GET"])
def analytics():
    """Return datasets for all dashboard charts."""
    return jsonify({
        "hourly_consumption": get_hourly_consumption(),
        "daily_consumption":  get_daily_consumption(),
        "tank_level_trend":   get_tank_level_trend(limit=50),
        "cost_trend":         get_cost_trend(limit=50)
    })


# ---------------------------------------------------------------------------
# GET /api/cost
# ---------------------------------------------------------------------------

@data_bp.route("/cost", methods=["GET"])
def cost():
    reading = get_latest_reading()
    if not reading:
        return jsonify({"error": "No data available yet."}), 404

    leak   = leak_predict(reading["flow_rate"], reading["tank_level"])
    result = calculate_dynamic_cost(
        reading["flow_rate"],
        reading["tank_level"],
        leak_detected=(leak["status"] == "Leak")
    )
    return jsonify(result)


# ---------------------------------------------------------------------------
# GET /api/conservation-score
# ---------------------------------------------------------------------------

@data_bp.route("/conservation-score", methods=["GET"])
def conservation_score():
    reading = get_latest_reading()
    if not reading:
        return jsonify({"error": "No data available yet."}), 404

    leak   = leak_predict(reading["flow_rate"], reading["tank_level"])
    result = calculate_conservation_score(
        reading["flow_rate"],
        reading["tank_level"],
        leak["status"]
    )
    return jsonify(result)


# ---------------------------------------------------------------------------
# POST /api/calculate-savings
# ---------------------------------------------------------------------------

@data_bp.route("/calculate-savings", methods=["POST"])
def calc_savings():
    """
    Body: { "reduction_percent": 10 }
    """
    body = request.get_json(silent=True) or {}
    reduction = body.get("reduction_percent")

    if reduction is None:
        return jsonify({"error": "reduction_percent is required."}), 400

    try:
        reduction = float(reduction)
        if not (1 <= reduction <= 99):
            raise ValueError()
    except (TypeError, ValueError):
        return jsonify({"error": "reduction_percent must be a number between 1 and 99."}), 400

    reading = get_latest_reading()
    if not reading:
        return jsonify({"error": "No data available yet."}), 404

    result = calculate_savings(reading["flow_rate"], reduction)
    return jsonify(result)


# ---------------------------------------------------------------------------
# GET /api/monitoring  (paginated live table)
# ---------------------------------------------------------------------------

@data_bp.route("/monitoring", methods=["GET"])
def monitoring():
    limit = int(request.args.get("limit", 50))
    rows  = get_recent_readings(limit=limit)
    return jsonify(rows)

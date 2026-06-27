"""
Cost Service — dynamic water cost simulator and conservation score generator.
"""

from datetime import datetime
import logging

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Rate constants  (adjust to your local utility tariff)
# ---------------------------------------------------------------------------
BASE_RATE_PER_LITRE   = 0.005   # ₹ per litre (base)
PEAK_RATE_MULTIPLIER  = 1.5     # multiplier during peak hours
LEAK_PENALTY          = 0.20    # 20 % cost penalty when leak detected

PEAK_HOURS = set(range(6, 10)) | set(range(17, 22))  # 6–9 AM and 5–9 PM


def _is_peak_hour() -> bool:
    return datetime.now().hour in PEAK_HOURS


def calculate_dynamic_cost(flow_rate: float, tank_level: float,
                            leak_detected: bool = False) -> dict:
    """
    Estimate the cost for the current reading.

    Returns a dict with:
        estimated_cost  – ₹ per minute at current flow
        rate_per_litre  – effective rate used
        category        – Low / Moderate / High / Critical
        reason          – human-readable explanation
    """
    rate = BASE_RATE_PER_LITRE

    reasons = []

    if _is_peak_hour():
        rate *= PEAK_RATE_MULTIPLIER
        reasons.append("peak-hour pricing applied")

    # Low tank → potential emergency draw (pumps work harder)
    if tank_level < 20:
        rate *= 1.2
        reasons.append("low tank level surcharge")

    if leak_detected:
        rate *= (1 + LEAK_PENALTY)
        reasons.append("leak-waste penalty applied")

    # Cost = flow_rate (L/min) × rate (₹/L)
    estimated_cost = round(flow_rate * rate, 4)

    if estimated_cost < 0.05:
        category = "Low"
    elif estimated_cost < 0.15:
        category = "Moderate"
    elif estimated_cost < 0.30:
        category = "High"
    else:
        category = "Critical"

    reason_text = (", ".join(reasons).capitalize() + ".") if reasons else "Standard pricing."

    return {
        "estimated_cost": estimated_cost,
        "rate_per_litre":  round(rate, 5),
        "category":        category,
        "reason":          reason_text,
        "is_peak_hour":    _is_peak_hour()
    }


def calculate_conservation_score(flow_rate: float, tank_level: float,
                                  leak_status: str) -> dict:
    """
    Generate a 0–100 conservation score.

    Factors
    -------
    - flow_rate   : lower is better (max 40 pts)
    - tank_level  : higher is better (max 30 pts)
    - leak_status : No Leak = full 30 pts
    """
    # Flow score (0–40): penalise high flow
    if flow_rate <= 5:
        flow_score = 40
    elif flow_rate <= 15:
        flow_score = int(40 - ((flow_rate - 5) / 10) * 20)
    else:
        flow_score = max(0, int(20 - ((flow_rate - 15) / 15) * 20))

    # Tank score (0–30): reward high tank level
    tank_score = int((tank_level / 100) * 30)

    # Leak score (0–30)
    leak_score = 30 if leak_status == "No Leak" else 0

    total = flow_score + tank_score + leak_score

    if total >= 80:
        category = "Excellent"
    elif total >= 60:
        category = "Good"
    elif total >= 40:
        category = "Moderate"
    else:
        category = "Needs Attention"

    return {
        "score":       total,
        "category":    category,
        "flow_score":  flow_score,
        "tank_score":  tank_score,
        "leak_score":  leak_score
    }


def calculate_savings(flow_rate: float, reduction_percent: float) -> dict:
    """
    What-if savings calculator.

    Parameters
    ----------
    flow_rate         : current flow rate (L/min)
    reduction_percent : e.g. 10.0 for 10 %

    Returns
    -------
    dict with current cost, projected cost, and savings per minute.
    """
    current = calculate_dynamic_cost(flow_rate, 50)["estimated_cost"]
    new_flow = flow_rate * (1 - reduction_percent / 100)
    projected = calculate_dynamic_cost(new_flow, 50)["estimated_cost"]
    savings = round(current - projected, 4)

    return {
        "reduction_percent": reduction_percent,
        "current_cost":      current,
        "projected_cost":    projected,
        "savings":           savings,
        "annual_savings":    round(savings * 60 * 24 * 365, 2)   # rough projection
    }

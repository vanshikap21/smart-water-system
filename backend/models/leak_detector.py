"""
Leak Detector Model — loads the trained Random Forest and exposes
a single predict() function used by the API routes.
"""

import os
import logging
import pickle
from datetime import datetime

import numpy as np

logger = logging.getLogger(__name__)

_BASE_DIR  = os.path.dirname(os.path.abspath(__file__))
MODEL_FILE = os.path.join(_BASE_DIR, "../ml/leak_detector.pkl")

_clf = None   # lazy-loaded singleton


def _load_model():
    global _clf
    if _clf is None:
        if not os.path.exists(MODEL_FILE):
            raise FileNotFoundError(
                f"Model file not found at {MODEL_FILE}. "
                "Run backend/ml/train_model.py first."
            )
        with open(MODEL_FILE, "rb") as f:
            _clf = pickle.load(f)
        logger.info("Leak detection model loaded from %s", MODEL_FILE)
    return _clf


def predict(flow_rate: float, tank_level: float) -> dict:
    """
    Run inference and return prediction, confidence, and a short reason.

    Parameters
    ----------
    flow_rate  : L/min
    tank_level : % (0–100)

    Returns
    -------
    dict with keys: status, confidence, reason
    """
    hour = datetime.now().hour
    features = np.array([[flow_rate, tank_level, hour]])

    clf = _load_model()
    prediction  = clf.predict(features)[0]           # 0 = No Leak, 1 = Leak
    probability = clf.predict_proba(features)[0]     # [p_no_leak, p_leak]

    status     = "Leak" if prediction == 1 else "No Leak"
    confidence = round(float(probability[prediction]) * 100, 1)

    # Generate a human-readable reason
    reason = _build_reason(status, flow_rate, tank_level, hour, confidence)

    return {
        "status":     status,
        "confidence": confidence,
        "reason":     reason
    }


def _build_reason(status: str, flow_rate: float, tank_level: float,
                  hour: int, confidence: float) -> str:
    if status == "Leak":
        parts = []
        if flow_rate > 20:
            parts.append(f"abnormally high flow rate ({flow_rate:.1f} L/min)")
        if tank_level < 20:
            parts.append(f"critically low tank level ({tank_level:.0f}%)")
        if hour in range(23, 6):
            parts.append("unusual usage detected at night")
        if not parts:
            parts.append("pattern matches known leak signatures")
        return "Leak likely due to: " + "; ".join(parts) + f" (confidence {confidence}%)."
    else:
        return (
            f"Normal usage pattern. Flow {flow_rate:.1f} L/min, "
            f"tank at {tank_level:.0f}%. No anomalies detected (confidence {confidence}%)."
        )

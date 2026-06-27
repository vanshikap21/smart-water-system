"""
ML Training Script — generates a synthetic labelled dataset and trains
a Random Forest Classifier for water leak detection.

Run:
    cd backend
    python ml/train_model.py
"""

import os
import pickle
import logging
import numpy as np
import pandas as pd
from sklearn.ensemble         import RandomForestClassifier
from sklearn.model_selection  import train_test_split
from sklearn.metrics          import classification_report, accuracy_score
from sklearn.preprocessing    import StandardScaler

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
logger = logging.getLogger(__name__)

SAVE_PATH = os.path.join(os.path.dirname(__file__), "leak_detector.pkl")
RANDOM_SEED = 42
N_SAMPLES   = 5000


# ---------------------------------------------------------------------------
# Dataset generation
# ---------------------------------------------------------------------------

def generate_dataset(n: int = N_SAMPLES) -> pd.DataFrame:
    """
    Synthetic dataset with realistic water usage patterns.

    Features:
        flow_rate  (L/min) : 0 – 50
        tank_level (%)     : 0 – 100
        hour               : 0 – 23

    Label (leak):
        1 if any of the following leak conditions are met:
          - Very high flow (> 25 L/min) especially at night
          - Low tank + high flow simultaneously
          - Sustained high flow outside peak hours
    """
    rng = np.random.default_rng(RANDOM_SEED)

    # --- Normal usage patterns ---
    flow_normal  = rng.uniform(1, 15, n)
    tank_normal  = rng.uniform(30, 100, n)
    hour_normal  = rng.integers(0, 24, n)

    # --- Inject anomalies into ~15 % of data ---
    n_leak = int(n * 0.15)
    idx    = rng.choice(n, n_leak, replace=False)

    flow_normal[idx]  = rng.uniform(20, 50, n_leak)   # high flow
    tank_normal[idx]  = rng.uniform(0,  30, n_leak)   # low tank

    # Leak label logic
    labels = np.zeros(n, dtype=int)
    labels[idx] = 1   # mark injected anomalies

    # Additional rule-based labelling for edge cases
    labels[(flow_normal > 25) & (hour_normal < 6)]  = 1   # night burst
    labels[(tank_normal < 15) & (flow_normal > 18)] = 1   # low tank + high flow

    df = pd.DataFrame({
        "flow_rate":  np.round(flow_normal, 2),
        "tank_level": np.round(tank_normal, 1),
        "hour":       hour_normal,
        "leak":       labels
    })

    logger.info("Dataset: %d samples, %d leaks (%.1f%%)",
                len(df), df["leak"].sum(), df["leak"].mean() * 100)
    return df


# ---------------------------------------------------------------------------
# Training
# ---------------------------------------------------------------------------

def train():
    df = generate_dataset()

    X = df[["flow_rate", "tank_level", "hour"]].values
    y = df["leak"].values

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=RANDOM_SEED, stratify=y
    )

    clf = RandomForestClassifier(
        n_estimators=150,
        max_depth=10,
        min_samples_split=5,
        class_weight="balanced",
        random_state=RANDOM_SEED,
        n_jobs=-1
    )
    clf.fit(X_train, y_train)

    y_pred = clf.predict(X_test)
    acc    = accuracy_score(y_test, y_pred)

    logger.info("Accuracy: %.4f", acc)
    logger.info("\n%s", classification_report(y_test, y_pred,
                                              target_names=["No Leak", "Leak"]))

    # Save model
    os.makedirs(os.path.dirname(SAVE_PATH), exist_ok=True)
    with open(SAVE_PATH, "wb") as f:
        pickle.dump(clf, f)
    logger.info("Model saved → %s", SAVE_PATH)

    return clf


if __name__ == "__main__":
    train()

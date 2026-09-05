"""Demo fraud-probability model.

Trained on synthetic data (see synthetic.py). Reported metrics describe the
generator, not the real world, and the API labels every prediction as such.
"""
from __future__ import annotations

import json
import logging
import threading
from pathlib import Path

from app.config import BASE_DIR
from app.ml.synthetic import FEATURES, generate

log = logging.getLogger(__name__)

MODEL_DIR = BASE_DIR / "app" / "ml" / "artifacts"
MODEL_PATH = MODEL_DIR / "refund_scam_rf.joblib"
METRICS_PATH = MODEL_DIR / "metrics.json"

_lock = threading.Lock()
_model = None
_metrics: dict | None = None

DISCLAIMER = "Demo model trained on synthetic data. Not validated on real transactions."


def train(persist: bool = True) -> tuple[object, dict]:
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.metrics import accuracy_score, roc_auc_score
    from sklearn.model_selection import train_test_split

    df = generate()
    x, y = df[FEATURES], df["is_scam"]
    x_train, x_test, y_train, y_test = train_test_split(
        x, y, test_size=0.25, random_state=42, stratify=y
    )

    clf = RandomForestClassifier(
        n_estimators=180, max_depth=9, min_samples_leaf=6, random_state=42, n_jobs=-1
    )
    clf.fit(x_train, y_train)

    proba = clf.predict_proba(x_test)[:, 1]
    metrics = {
        "model": "RandomForestClassifier",
        "trained_on": "synthetic",
        "samples": int(len(df)),
        "accuracy": round(float(accuracy_score(y_test, clf.predict(x_test))), 4),
        "roc_auc": round(float(roc_auc_score(y_test, proba)), 4),
        "feature_importance": {
            f: round(float(w), 4) for f, w in zip(FEATURES, clf.feature_importances_)
        },
        "disclaimer": DISCLAIMER,
    }

    if persist:
        import joblib

        MODEL_DIR.mkdir(parents=True, exist_ok=True)
        joblib.dump(clf, MODEL_PATH)
        METRICS_PATH.write_text(json.dumps(metrics, indent=2), encoding="utf-8")

    return clf, metrics


def _load() -> tuple[object | None, dict]:
    global _model, _metrics
    with _lock:
        if _model is not None:
            return _model, _metrics or {}
        try:
            if MODEL_PATH.exists() and METRICS_PATH.exists():
                import joblib

                _model = joblib.load(MODEL_PATH)
                _metrics = json.loads(METRICS_PATH.read_text(encoding="utf-8"))
            else:
                _model, _metrics = train()
        except Exception as exc:  # pragma: no cover - model stays optional
            log.warning("ML model unavailable, falling back to rules only: %s", exc)
            _model, _metrics = None, {"error": str(exc), "disclaimer": DISCLAIMER}
        return _model, _metrics or {}


def metrics() -> dict:
    _, m = _load()
    return m


def predict_probability(features: dict) -> float | None:
    """Return P(refund scam) in 0..1, or None when the model cannot be used."""
    model, _ = _load()
    if model is None:
        return None
    try:
        import pandas as pd

        row = pd.DataFrame([[float(features.get(f, 0)) for f in FEATURES]], columns=FEATURES)
        return float(model.predict_proba(row)[0][1])
    except Exception as exc:  # pragma: no cover
        log.warning("ML prediction failed: %s", exc)
        return None


def feature_vector_from_context(ctx, message_score: int = 0) -> dict:
    """Map a RefundContext onto the model's feature space."""
    return {
        "transaction_amount": ctx.refund_amount,
        "account_age_days": ctx.sender_account_age_days,
        "transaction_frequency": 6 if not ctx.sender_known else 40,
        "time_to_refund_seconds": max(ctx.seconds_since_payment, 1),
        "refund_amount_ratio": 1.0,
        "previous_suspicious_activity": int(ctx.sender_suspicious_history),
        "refund_destination_match": int(
            ctx.normalised_destination() == ctx.normalised_sender() or not ctx.refund_destination
        ),
        "previous_reports": int(ctx.sender_prior_reports > 0),
        "urgency_score": message_score,
    }

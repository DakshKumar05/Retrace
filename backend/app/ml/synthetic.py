"""Synthetic training data for the demo fraud model.

There is no real transaction data behind this project, so the model is trained
on a generator whose labelling rule encodes the refund-scam pattern described in
the brief. This is honest demo scaffolding, not a production model.

Where a public number exists, a distribution is anchored to it instead of a
guess:
  - Average loss per reported UPI fraud case was ~Rs 8,100 in FY24 and
    ~Rs 7,760 in FY25 (RBI/Parliament data: Rs 1,087cr / 13.42 lakh cases,
    Rs 981cr / 12.64 lakh cases). The fraud-class transaction_amount is
    centred there. Everything else here remains a design assumption, not a
    fitted statistic, and the model card says so.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

FEATURES = [
    "transaction_amount",
    "account_age_days",
    "transaction_frequency",
    "time_to_refund_seconds",
    "refund_amount_ratio",
    "previous_suspicious_activity",
    "refund_destination_match",
    "previous_reports",
    "urgency_score",
]


def generate(n: int = 6000, seed: int = 7) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    n_fraud = n // 3
    n_legit = n - n_fraud

    legit = pd.DataFrame(
        {
            "transaction_amount": rng.lognormal(6.6, 0.9, n_legit).clip(50, 120_000),
            "account_age_days": rng.integers(60, 3200, n_legit),
            "transaction_frequency": rng.integers(4, 90, n_legit),
            "time_to_refund_seconds": rng.integers(1800, 604_800, n_legit),
            "refund_amount_ratio": rng.normal(1.0, 0.05, n_legit).clip(0.2, 1.0),
            "previous_suspicious_activity": rng.binomial(1, 0.04, n_legit),
            "refund_destination_match": rng.binomial(1, 0.93, n_legit),
            "previous_reports": rng.binomial(1, 0.03, n_legit),
            "urgency_score": rng.integers(0, 35, n_legit),
        }
    )
    legit["is_scam"] = 0

    fraud = pd.DataFrame(
        {
            # mean ~ Rs 7,900, matching the FY24-25 average reported UPI fraud loss.
            "transaction_amount": rng.lognormal(8.82, 0.55, n_fraud).clip(1500, 150_000),
            "account_age_days": rng.integers(1, 70, n_fraud),
            "transaction_frequency": rng.integers(1, 12, n_fraud),
            "time_to_refund_seconds": rng.integers(45, 2400, n_fraud),
            "refund_amount_ratio": rng.normal(1.0, 0.02, n_fraud).clip(0.8, 1.0),
            "previous_suspicious_activity": rng.binomial(1, 0.62, n_fraud),
            "refund_destination_match": rng.binomial(1, 0.09, n_fraud),
            "previous_reports": rng.binomial(1, 0.55, n_fraud),
            "urgency_score": rng.integers(45, 100, n_fraud),
        }
    )
    fraud["is_scam"] = 1

    df = pd.concat([legit, fraud], ignore_index=True)

    # Blur the boundary so the model cannot memorise a trivial split.
    flip = rng.random(len(df)) < 0.045
    df.loc[flip, "is_scam"] = 1 - df.loc[flip, "is_scam"]

    return df.sample(frac=1.0, random_state=seed).reset_index(drop=True)

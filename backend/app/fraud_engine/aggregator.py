"""Combines the four independent detectors into one refund safety verdict.

    rules  +  ML  +  message  +  network   ->   risk 0-100
                                           ->   safety = 100 - risk

The brief shows a "Refund Safety Score" of 18/100 marked CRITICAL and elsewhere
a score of 94/100 also marked CRITICAL. Those are two different scales, so both
are returned explicitly and never conflated:

    risk_score    higher = more dangerous  (drives the risk level)
    safety_score  higher = safer           (= 100 - risk_score, shown as "x / 100 safe")
"""
from __future__ import annotations

from dataclasses import dataclass, field

from app.fraud_engine.rules import (
    RefundContext,
    RuleResult,
    Signal,
    evaluate,
    recommendation_for,
    risk_level,
)
from app.ml import model as ml_model

# How much each independent detector contributes.
W_RULES = 0.45
W_ML = 0.25
W_MESSAGE = 0.15
W_NETWORK = 0.15

CORROBORATION_THRESHOLD = 75
CORROBORATION_BONUS = 4
CEILING = 98  # never assert certainty


@dataclass
class RiskVerdict:
    risk_score: int
    safety_score: int
    risk_level: str
    recommendation: str
    rule_score: int
    ml_probability: float | None
    message_score: int
    network_score: int
    signals: list[Signal] = field(default_factory=list)
    components: list[dict] = field(default_factory=list)
    ml_disclaimer: str = ml_model.DISCLAIMER

    @property
    def reasons(self) -> list[str]:
        """Signal labels, in order, without repeats.

        Two signals can carry the same label but different details (two phrases
        matching the same pattern group, say). The details keep them apart in
        the full explanation; a summary line that says the same sentence twice
        just reads like a bug.
        """
        return list(dict.fromkeys(s.label for s in self.signals))

    def as_dict(self) -> dict:
        return {
            "risk_score": self.risk_score,
            "safety_score": self.safety_score,
            "risk_level": self.risk_level,
            "recommendation": self.recommendation,
            "reasons": self.reasons,
            "signals": [s.as_dict() for s in self.signals],
            "components": self.components,
            "rule_score": self.rule_score,
            "ml_probability": self.ml_probability,
            "message_score": self.message_score,
            "network_score": self.network_score,
            "ml_disclaimer": self.ml_disclaimer,
        }


def assess_refund(
    ctx: RefundContext,
    network_score: int = 0,
    network_detail: str | None = None,
    use_ml: bool = True,
) -> RiskVerdict:
    rules: RuleResult = evaluate(ctx)

    ml_probability = None
    if use_ml:
        ml_probability = ml_model.predict_probability(
            ml_model.feature_vector_from_context(ctx, rules.message_score)
        )

    ml_component = round((ml_probability or 0.0) * 100)
    present = [(W_RULES, rules.rule_score)]
    if ml_probability is not None:
        present.append((W_ML, ml_component))
    if rules.message_score:
        present.append((W_MESSAGE, rules.message_score))
    if network_score:
        present.append((W_NETWORK, network_score))

    total_weight = sum(w for w, _ in present) or 1.0
    blended = sum(w * v for w, v in present) / total_weight

    strong = sum(1 for _, v in present if v >= CORROBORATION_THRESHOLD)
    if strong >= 3:
        blended += CORROBORATION_BONUS

    risk = int(min(round(blended), CEILING))
    level = risk_level(risk)

    signals = list(rules.signals)
    if ml_probability is not None and ml_component >= 50:
        signals.append(
            Signal(
                "ML_PATTERN_MATCH",
                "Behaviour resembles known refund-scam sequences",
                min(ml_component // 5, 20),
                category="ML",
                detail=(
                    f"Demo model probability {ml_component}%. {ml_model.DISCLAIMER} "
                    "A model score is not proof of fraud."
                ),
            )
        )
    if network_score >= 40:
        signals.append(
            Signal(
                "NETWORK_LINKED",
                "Sender is connected to other flagged accounts",
                min(network_score // 5, 20),
                category="NETWORK",
                detail=network_detail,
            )
        )
    signals.extend(rules.message_signals)

    components = [
        {"name": "Rules engine", "value": rules.rule_score, "weight": W_RULES, "unit": "score"},
        {
            "name": "Demo ML model",
            "value": ml_component if ml_probability is not None else None,
            "weight": W_ML,
            "unit": "probability",
        },
        {"name": "Message analysis", "value": rules.message_score or None, "weight": W_MESSAGE, "unit": "score"},
        {"name": "Network analysis", "value": network_score or None, "weight": W_NETWORK, "unit": "score"},
    ]

    return RiskVerdict(
        risk_score=risk,
        safety_score=100 - risk,
        risk_level=level,
        recommendation=recommendation_for(risk),
        rule_score=rules.rule_score,
        ml_probability=round(ml_probability, 4) if ml_probability is not None else None,
        message_score=rules.message_score,
        network_score=network_score,
        signals=sorted(signals, key=lambda s: -s.weight),
        components=components,
    )

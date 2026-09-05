"""The refund safety rules engine.

This answers the product's central question — "is it safe for this user to
refund this payment?" — rather than the usual "is this payment fraudulent?".

Every rule is a pure function of a RefundContext, carries a fixed weight, and
returns a human sentence. Nothing here is a black box.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from app.nlp.analyzer import analyze_message


@dataclass
class RefundContext:
    """Everything the engine is allowed to look at."""

    refund_amount: float
    original_sender: str
    refund_destination: str
    seconds_since_payment: int

    sender_known: bool = True
    sender_account_age_days: int = 365
    sender_suspicious_history: bool = False
    sender_prior_reports: int = 0
    prior_refund_requests: int = 0
    user_median_credit: float = 2000.0
    message: str | None = None

    def normalised_sender(self) -> str:
        return (self.original_sender or "").strip().lower()

    def normalised_destination(self) -> str:
        return (self.refund_destination or "").strip().lower()


@dataclass
class Signal:
    code: str
    label: str
    weight: int
    category: str = "RULE"
    detail: str | None = None

    def as_dict(self) -> dict:
        return {
            "code": self.code,
            "label": self.label,
            "weight": self.weight,
            "category": self.category,
            "detail": self.detail,
        }


@dataclass
class RuleResult:
    rule_score: int
    raw_score: int
    signals: list[Signal] = field(default_factory=list)
    message_score: int = 0
    message_signals: list[Signal] = field(default_factory=list)

    @property
    def reasons(self) -> list[str]:
        return [s.label for s in self.signals]


# Weights are exactly the ones specified in the product brief.
W_UNKNOWN_SENDER = 15
W_FAST_REFUND = 20
W_DESTINATION_MISMATCH = 25
W_NEW_ACCOUNT = 15
W_UNUSUAL_AMOUNT = 10
W_PRIOR_SUSPICIOUS = 15
W_REPEATED_REQUESTS = 15
W_URGENCY_LANGUAGE = 10

FAST_REFUND_SECONDS = 600  # ten minutes
NEW_ACCOUNT_DAYS = 30
MAX_RAW = (
    W_UNKNOWN_SENDER + W_FAST_REFUND + W_DESTINATION_MISMATCH + W_NEW_ACCOUNT
    + W_UNUSUAL_AMOUNT + W_PRIOR_SUSPICIOUS + W_REPEATED_REQUESTS + W_URGENCY_LANGUAGE
)  # 125


def _minutes(seconds: int) -> str:
    if seconds < 90:
        return f"{seconds} seconds"
    if seconds < 5400:
        return f"{round(seconds / 60)} minutes"
    return f"{round(seconds / 3600, 1)} hours"


def evaluate(ctx: RefundContext) -> RuleResult:
    signals: list[Signal] = []

    if not ctx.sender_known:
        signals.append(
            Signal(
                "UNKNOWN_SENDER",
                "Money came from an account you have never transacted with",
                W_UNKNOWN_SENDER,
                detail=f"No prior history with {ctx.original_sender}.",
            )
        )

    if ctx.seconds_since_payment <= FAST_REFUND_SECONDS:
        signals.append(
            Signal(
                "FAST_REFUND_REQUEST",
                "Refund was requested very soon after the payment arrived",
                W_FAST_REFUND,
                detail=(
                    f"{_minutes(ctx.seconds_since_payment)} after the credit. Genuine mistaken "
                    "payments are usually resolved through the bank, not within minutes over chat."
                ),
            )
        )

    if ctx.normalised_destination() and ctx.normalised_destination() != ctx.normalised_sender():
        signals.append(
            Signal(
                "DESTINATION_MISMATCH",
                "Refund destination is not the account the money came from",
                W_DESTINATION_MISMATCH,
                detail=f"Paid in from {ctx.original_sender}, refund requested to {ctx.refund_destination}.",
            )
        )

    if ctx.sender_account_age_days <= NEW_ACCOUNT_DAYS:
        signals.append(
            Signal(
                "NEW_SENDER_ACCOUNT",
                "The sending account was created recently",
                W_NEW_ACCOUNT,
                detail=f"Account age about {ctx.sender_account_age_days} days.",
            )
        )

    if _is_unusual_amount(ctx):
        signals.append(
            Signal(
                "UNUSUAL_AMOUNT",
                "Amount is well outside this account's normal incoming payments",
                W_UNUSUAL_AMOUNT,
                detail=(
                    f"Rs {ctx.refund_amount:,.0f} against a typical credit of "
                    f"Rs {ctx.user_median_credit:,.0f}."
                ),
            )
        )

    if ctx.sender_suspicious_history or ctx.sender_prior_reports > 0:
        signals.append(
            Signal(
                "SENDER_SUSPICIOUS_HISTORY",
                "The sender has been flagged in earlier activity",
                W_PRIOR_SUSPICIOUS,
                detail=f"{ctx.sender_prior_reports} earlier report(s) associated with this handle.",
            )
        )

    if ctx.prior_refund_requests >= 1:
        signals.append(
            Signal(
                "REPEATED_REFUND_REQUESTS",
                "More than one refund request tied to the same payment",
                W_REPEATED_REQUESTS,
                detail=f"{ctx.prior_refund_requests + 1} requests recorded.",
            )
        )

    message_score = 0
    message_signals: list[Signal] = []
    if ctx.message:
        analysis = analyze_message(ctx.message)
        message_score = analysis.score
        message_signals = [Signal(**s) for s in analysis.signals]
        if any(s.code in {"URGENCY", "PRESSURE"} for s in message_signals):
            signals.append(
                Signal(
                    "URGENCY_LANGUAGE",
                    "The request uses urgency or pressure to rush you",
                    W_URGENCY_LANGUAGE,
                    detail="; ".join(analysis.matched_phrases[:3]) or None,
                )
            )

    raw = sum(s.weight for s in signals)
    return RuleResult(
        rule_score=normalise(raw),
        raw_score=raw,
        signals=sorted(signals, key=lambda s: -s.weight),
        message_score=message_score,
        message_signals=message_signals,
    )


def _is_unusual_amount(ctx: RefundContext) -> bool:
    median = max(ctx.user_median_credit, 1.0)
    if ctx.refund_amount >= median * 3:
        return True
    # Round five-figure-ish amounts are the shape this scam usually takes.
    return ctx.refund_amount >= 5000 and ctx.refund_amount % 1000 == 0


def normalise(raw: int) -> int:
    """Map a raw weight sum onto 0-100 without letting signals stack past the top.

    Linear up to 60, then compressed, so that adding a seventh signal to an
    already-critical case cannot push the score to a misleading 100.
    """
    raw = max(raw, 0)
    if raw <= 60:
        return min(raw, 100)
    return min(int(round(60 + (raw - 60) * 0.53)), 100)


def risk_level(score: int) -> str:
    if score <= 30:
        return "LOW"
    if score <= 60:
        return "MEDIUM"
    if score <= 80:
        return "HIGH"
    return "CRITICAL"


def recommendation_for(score: int) -> str:
    if score <= 30:
        return "SAFE_TO_REFUND"
    if score <= 60:
        return "VERIFY_BEFORE_REFUND"
    if score <= 80:
        return "USE_SAFE_REFUND"
    return "DO_NOT_REFUND"

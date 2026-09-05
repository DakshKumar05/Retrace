"""Refund analysis and the simulated refund flows.

No real money moves anywhere in this file. When Razorpay *test* keys are present
the safe refund path is labelled Test Mode; otherwise it is labelled Simulated.
Either way the effect is confined to this database.
"""
from __future__ import annotations

import logging
from statistics import median

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import settings
from app.fraud_engine import RefundContext, RiskVerdict, assess_refund
from app.models import Alert, FraudSignal, RefundRequest, RiskAssessment, Transaction, User
from app.network import network_risk_for_handle
from app.services import razorpay_client
from app.services.references import unique_reference

log = logging.getLogger("retrace.refunds")


def user_median_credit(db: Session, user_id: int) -> float:
    amounts = db.scalars(
        select(Transaction.amount)
        .where(Transaction.user_id == user_id, Transaction.direction == "credit")
        .order_by(Transaction.created_at.desc())
        .limit(40)
    ).all()
    return float(median(amounts)) if amounts else 2000.0


def build_context(
    db: Session,
    user: User,
    transaction: Transaction | None,
    refund_amount: float,
    original_sender: str,
    refund_destination: str,
    seconds_since_payment: int,
    message: str | None = None,
) -> RefundContext:
    prior = 0
    if transaction is not None:
        prior = int(
            db.scalar(
                select(func.count(RefundRequest.id)).where(
                    RefundRequest.transaction_id == transaction.id
                )
            )
            or 0
        )
    return RefundContext(
        refund_amount=refund_amount,
        original_sender=original_sender,
        refund_destination=refund_destination,
        seconds_since_payment=seconds_since_payment,
        sender_known=transaction.sender_known if transaction else False,
        sender_account_age_days=transaction.sender_account_age_days if transaction else 5,
        sender_suspicious_history=transaction.sender_suspicious_history if transaction else False,
        sender_prior_reports=transaction.sender_prior_reports if transaction else 0,
        prior_refund_requests=max(prior - 1, 0),
        user_median_credit=user_median_credit(db, user.id),
        message=message,
    )


def analyse(db: Session, ctx: RefundContext) -> RiskVerdict:
    network_score, network_detail = network_risk_for_handle(db, ctx.original_sender)
    return assess_refund(ctx, network_score=network_score, network_detail=network_detail)


def persist_assessment(
    db: Session,
    user: User,
    verdict: RiskVerdict,
    transaction: Transaction | None = None,
    refund_request: RefundRequest | None = None,
    subject: str = "REFUND",
) -> RiskAssessment:
    assessment = RiskAssessment(
        user_id=user.id,
        transaction_id=transaction.id if transaction else None,
        refund_request_id=refund_request.id if refund_request else None,
        subject=subject,
        rule_score=verdict.rule_score,
        ml_probability=verdict.ml_probability or 0.0,
        message_score=verdict.message_score,
        network_score=verdict.network_score,
        risk_score=verdict.risk_score,
        safety_score=verdict.safety_score,
        risk_level=verdict.risk_level,
        recommendation=verdict.recommendation,
    )
    db.add(assessment)
    db.flush()
    for signal in verdict.signals:
        db.add(
            FraudSignal(
                assessment_id=assessment.id,
                code=signal.code,
                label=signal.label,
                weight=signal.weight,
                category=signal.category,
                detail=signal.detail,
            )
        )
    return assessment


def create_refund_request(
    db: Session,
    user: User,
    transaction: Transaction,
    refund_destination: str,
    verdict: RiskVerdict,
    seconds_since_payment: int,
    message: str | None = None,
    channel: str = "WHATSAPP",
    amount: float | None = None,
) -> RefundRequest:
    matches = (refund_destination or "").strip().lower() == transaction.sender_handle.strip().lower()
    refund = RefundRequest(
        reference=unique_reference(db, RefundRequest.reference, "RFQ"),
        transaction_id=transaction.id,
        user_id=user.id,
        amount=amount if amount is not None else transaction.amount,
        original_sender=transaction.sender_handle,
        refund_destination=refund_destination,
        destination_matches_sender=matches,
        seconds_since_payment=seconds_since_payment,
        channel=channel,
        message=message,
        status="BLOCKED" if verdict.risk_level in {"HIGH", "CRITICAL"} else "PENDING",
        risk_score=verdict.risk_score,
        safety_score=verdict.safety_score,
        risk_level=verdict.risk_level,
        recommendation=verdict.recommendation,
    )
    db.add(refund)
    transaction.refund_requested = True
    transaction.risk_score = max(transaction.risk_score, verdict.risk_score)
    transaction.label = (
        "HIGH_RISK" if verdict.risk_level == "CRITICAL"
        else "SUSPICIOUS" if verdict.risk_level in {"HIGH", "MEDIUM"} else transaction.label
    )
    db.flush()
    return refund


def raise_alert(db: Session, user: User, verdict: RiskVerdict, transaction: Transaction) -> Alert:
    alert = Alert(
        user_id=user.id,
        transaction_id=transaction.id,
        title=f"{verdict.risk_level.title()} risk refund request on {transaction.reference}",
        body="; ".join(verdict.reasons[:3]) or "Refund behaviour flagged for review.",
        severity=verdict.risk_level,
    )
    db.add(alert)
    return alert


def refund_mode() -> str:
    return "RAZORPAY_TEST_MODE" if settings.razorpay_test_mode else "SIMULATED"


# ------------------------------------------------------------------- settlement
# Marking a refund "done" without moving the balance leaves the account showing
# money it no longer has, and the transaction list showing no sign anything
# happened. These record the movement so the ledger and the balance agree.

def _debit(
    db: Session, user: User, amount: float, to_handle: str, label: str,
    note: str, status: str = "COMPLETED", risk_score: int = 0,
) -> Transaction:
    """Money leaving the account, written to the ledger and taken off the balance."""
    debit = Transaction(
        reference=unique_reference(db, Transaction.reference, "TX"),
        user_id=user.id,
        direction="debit",
        amount=amount,
        sender_handle=user.upi_id,
        receiver_handle=to_handle,
        payment_method="UPI",
        status=status,
        label=label,
        risk_score=risk_score,
        note=note,
    )
    db.add(debit)
    user.balance -= amount
    return debit


def settle_safe_refund(db: Session, user: User, refund: RefundRequest, transaction: Transaction) -> None:
    """The money goes back to the account that paid it. Nothing is lost."""
    _debit(
        db, user, refund.amount, transaction.sender_handle, "SAFE",
        note=f"Safe refund returned along the original payment {transaction.reference}.",
    )


def settle_manual_transfer(
    db: Session, user: User, refund: RefundRequest, transaction: Transaction
) -> float:
    """The user sent it on themselves. Returns the net loss.

    The transfer out always happens. The clawback only follows when the credit
    was risky enough to be a scam in the first place — a low-risk manual
    transfer is just a payment, and reversing it would be inventing a loss.
    """
    _debit(
        db, user, refund.amount, refund.refund_destination, "HIGH_RISK",
        note=f"Manual transfer to {refund.refund_destination}.",
        risk_score=refund.risk_score,
    )

    if refund.risk_level not in {"HIGH", "CRITICAL"}:
        return 0.0

    # The second debit. Two of them land against a single credit, so the money
    # is gone once — which is the whole mechanism of this scam.
    _debit(
        db, user, refund.amount, transaction.sender_handle, "HIGH_RISK",
        note="The original credit was disputed and reversed by the bank.",
        status="REVERSED", risk_score=refund.risk_score,
    )
    db.add(
        Alert(
            user_id=user.id,
            transaction_id=transaction.id,
            title="The original payment was reversed",
            body=(
                f"Rs {refund.amount:,.0f} was taken back after you had already transferred it on. "
                "That is the second loss this scam depends on."
            ),
            severity="CRITICAL",
        )
    )
    return refund.amount


def initiate_safe_refund(db: Session, refund: RefundRequest, transaction: Transaction) -> dict:
    """Return the money along the original payment rail instead of to a new handle.

    When the credit arrived through Razorpay Test Mode this calls the real
    refund API against the original payment id. That endpoint takes no
    destination, so the money is structurally unable to reach the handle the
    scammer supplied. Without provider keys the same outcome is recorded
    locally instead.
    """
    live = razorpay_client.enabled() and bool(transaction.provider_payment_id)

    if live:
        try:
            result = razorpay_client.create_refund(
                transaction.provider_payment_id or "",
                refund.amount,
                notes={
                    "reason": "Retrace safe refund",
                    "refund_request": refund.reference,
                    "risk_score": str(refund.risk_score),
                },
            )
        except razorpay_client.RazorpayError as exc:
            log.warning("Razorpay refund failed for %s: %s", refund.reference, exc)
            raise
        provider_id = result.get("id", "")
        provider_status = (result.get("status") or "pending").upper()
    else:
        provider_id = f"rfnd_demo_{transaction.reference.lower().removeprefix('tx')}"
        provider_status = "PROCESSING"

    refund.provider_refund_id = provider_id
    refund.provider_status = provider_status
    refund.status = "SAFE_REFUND_INITIATED"
    refund.refund_destination = transaction.sender_handle
    refund.destination_matches_sender = True

    db.add(
        Alert(
            user_id=refund.user_id,
            transaction_id=transaction.id,
            title=f"Safe refund started for {transaction.reference}",
            body=(
                "The refund was routed back through the original payment instead of a new "
                "UPI handle, so the money can only reach the account it came from."
            ),
            severity="LOW",
        )
    )
    return {
        "refund_id": provider_id,
        "status": provider_status,
        "amount": refund.amount,
        "destination": transaction.sender_handle,
        "mode": "RAZORPAY_TEST_MODE" if live else refund_mode(),
        "message": (
            "Refund routed back through the original payment. "
            + (
                f"Razorpay processed it against payment {transaction.provider_payment_id}, "
                "which can only pay the original method. No live funds are involved."
                if live
                else "This is a simulated refund. No funds have moved."
            )
        ),
    }

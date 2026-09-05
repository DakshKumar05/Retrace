"""Runs the whole refund scam end to end against synthetic data.

Every number here is fabricated for demonstration. Nothing in this flow touches
a bank, a card, or a real payment provider.
"""
from __future__ import annotations

from datetime import timedelta

from sqlalchemy.orm import Session

from app.models import (
    Alert,
    RefundRequest,
    Transaction,
    TransactionEvent,
    User,
    utcnow,
)
from app.services import incident_service, refund_service
from app.services.references import unique_reference

SCAM_MESSAGE = (
    "Hi bro, I accidentally sent Rs 8,000 to you just now. Please send it back urgently to my "
    "wife's UPI xyz987@upi, my account isn't working. Please help fast, it is an emergency."
)


def _tx_reference(db: Session) -> str:
    return unique_reference(db, Transaction.reference, "TX")


def run(db: Session, user: User, unsafe: bool) -> dict:
    now = utcnow()
    start = now - timedelta(minutes=9)

    transaction = Transaction(
        reference=_tx_reference(db),
        user_id=user.id,
        direction="credit",
        amount=8000.0,
        sender_handle="unknown@upi",
        receiver_handle=user.upi_id,
        payment_method="UPI",
        status="COMPLETED",
        label="SUSPICIOUS",
        risk_score=0,
        sender_known=False,
        sender_account_age_days=6,
        sender_prior_reports=3,
        sender_suspicious_history=True,
        refund_requested=True,
        note="Simulated incoming payment from an unknown sender.",
        created_at=start,
    )
    db.add(transaction)
    db.flush()

    behaviour = [
        (0, "payment_received", "Rs 8,000 received", "Credited from unknown@upi.", "info"),
        (3, "refund_requested", "Refund request received", "Sender says the payment was a mistake.", "warning"),
        (4, "contact", "Sender contacted you", "Message received over WhatsApp.", "warning"),
        (5, "destination_supplied", "A different UPI ID was supplied", "xyz987@upi, not the paying account.", "critical"),
    ]
    for minutes, kind, title, detail, severity in behaviour:
        db.add(
            TransactionEvent(
                transaction_id=transaction.id,
                occurred_at=start + timedelta(minutes=minutes),
                kind=kind,
                title=title,
                detail=detail,
                severity=severity,
            )
        )

    ctx = refund_service.build_context(
        db,
        user,
        transaction,
        refund_amount=8000.0,
        original_sender="unknown@upi",
        refund_destination="xyz987@upi",
        seconds_since_payment=240,
        message=SCAM_MESSAGE,
    )
    verdict = refund_service.analyse(db, ctx)

    refund = refund_service.create_refund_request(
        db, user, transaction, "xyz987@upi", verdict, 240, message=SCAM_MESSAGE
    )
    refund_service.persist_assessment(db, user, verdict, transaction, refund)
    refund_service.raise_alert(db, user, verdict, transaction)
    db.flush()

    steps = [
        {"step": 1, "title": "Rs 8,000 received", "detail": "From unknown@upi.", "at": start},
        {
            "step": 2,
            "title": "Refund request received",
            "detail": "\"Sorry, I sent this by mistake. Please send it back urgently.\"",
            "at": start + timedelta(minutes=3),
        },
        {
            "step": 3,
            "title": "Risk engine ran",
            "detail": f"Refund safety {verdict.safety_score}/100, risk {verdict.risk_score}/100.",
            "at": start + timedelta(minutes=4),
        },
        {
            "step": 4,
            "title": f"{verdict.risk_level} risk",
            "detail": verdict.reasons[0] if verdict.reasons else "Pattern flagged.",
            "at": start + timedelta(minutes=4, seconds=5),
        },
    ]

    incident = None
    completeness = None

    if unsafe:
        refund.status = "MANUAL_TRANSFER"
        db.add(
            TransactionEvent(
                transaction_id=transaction.id,
                occurred_at=start + timedelta(minutes=8),
                kind="manual_refund",
                title="Rs 8,000 transferred manually",
                detail="Sent to xyz987@upi, a different account from the one that paid in.",
                severity="critical",
            )
        )
        db.add(
            Transaction(
                reference=_tx_reference(db),
                user_id=user.id,
                direction="debit",
                amount=8000.0,
                sender_handle=user.upi_id,
                receiver_handle="xyz987@upi",
                payment_method="UPI",
                status="COMPLETED",
                label="HIGH_RISK",
                risk_score=verdict.risk_score,
                sender_known=False,
                sender_account_age_days=6,
                note="Simulated manual refund to a mismatched destination.",
                created_at=start + timedelta(minutes=8),
            )
        )
        db.add(
            TransactionEvent(
                transaction_id=transaction.id,
                occurred_at=start + timedelta(minutes=9),
                kind="pattern_detected",
                title="High-risk pattern detected",
                detail="Payment, fast refund request and destination mismatch in sequence.",
                severity="critical",
            )
        )
        db.flush()
        db.refresh(transaction)

        incident = incident_service.create_incident(
            db, user, transaction, refund, verdict.risk_score, verdict.risk_level,
            scam_message=SCAM_MESSAGE,
        )
        incident_service.build_timeline_from_transaction(db, incident, transaction, refund)
        incident_service.enable_safe_mode(
            db, user, "Turned on automatically after a critical refund pattern."
        )
        incident_service.add_event(
            db, incident, "Safe Mode turned on",
            "New beneficiaries and high-risk transfers now need an extra confirmation.",
            severity="warning",
        )
        incident_service.seed_evidence_placeholders(
            db,
            incident,
            present=[
                "bank_statement", "original_transaction", "refund_transaction",
                "whatsapp", "call_log", "payment_receipt",
            ],
        )
        incident_service.add_event(
            db, incident, "Evidence placeholders created",
            "Six of seven expected items are accounted for.",
        )
        db.flush()
        completeness = incident_service.completeness(db, incident.id, user.id)

        steps.append(
            {
                "step": 5,
                "title": "Rs 8,000 refunded manually",
                "detail": "Sent to xyz987@upi. The money left the account.",
                "at": start + timedelta(minutes=8),
            }
        )
        steps.append(
            {
                "step": 6,
                "title": f"Incident {incident.case_id} created",
                "detail": "Safe Mode is on and the evidence checklist has been started.",
                "at": start + timedelta(minutes=9),
            }
        )
    else:
        result = refund_service.initiate_safe_refund(db, refund, transaction)
        db.add(
            TransactionEvent(
                transaction_id=transaction.id,
                occurred_at=start + timedelta(minutes=6),
                kind="safe_refund",
                title="Safe refund started",
                detail="Money routed back through the original payment, not to the new handle.",
                severity="info",
            )
        )
        steps.append(
            {
                "step": 5,
                "title": "Safe refund started",
                "detail": f"{result['refund_id']} — {result['message']}",
                "at": start + timedelta(minutes=6),
            }
        )

    db.commit()
    db.refresh(transaction)
    db.refresh(refund)
    if incident is not None:
        db.refresh(incident)

    return {
        "transaction": transaction,
        "refund_request": refund,
        "analysis": verdict.as_dict(),
        "steps": steps,
        "incident": incident,
        "completeness": completeness,
        "safe_mode_enabled": user.safe_mode_enabled,
    }


def reset(db: Session, user: User) -> None:
    """Clear simulated artefacts so the demo can be run again cleanly."""
    from app.config import settings
    from app.database.seed import DEMO_STARTING_BALANCE, seed_user_data

    for incident in list(user.incidents):
        db.delete(incident)
    for tx in list(user.transactions):
        db.delete(tx)
    db.query(Alert).filter(Alert.user_id == user.id).delete()
    db.query(RefundRequest).filter(RefundRequest.user_id == user.id).delete()
    user.safe_mode_enabled = False
    user.safe_mode_activated_at = None
    # Protected funds are held out of `balance`, so returning them keeps the
    # account whole instead of losing the amount on every reset.
    user.balance += user.protected_balance
    user.protected_balance = 0.0
    if user.email == settings.demo_email.lower():
        user.balance = DEMO_STARTING_BALANCE
    db.flush()
    seed_user_data(db, user)
    db.commit()

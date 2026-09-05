"""Incident lifecycle: creation, timeline assembly and completeness scoring."""
from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import (
    REQUIRED_EVIDENCE,
    Alert,
    Evidence,
    Incident,
    IncidentEvent,
    RefundRequest,
    Transaction,
    User,
    utcnow,
)

EVIDENCE_LABELS = {
    "bank_statement": "Bank statement showing the incoming credit",
    "original_transaction": "Screenshot of the original transaction",
    "refund_transaction": "Screenshot of the refund you sent",
    "whatsapp": "WhatsApp conversation with the sender",
    "sms": "SMS messages",
    "call_log": "Call log",
    "call_recording": "Call recording",
    "payment_receipt": "Payment receipt",
    "bank_complaint": "Bank complaint",
    "bank_email": "Email from your bank",
    "complaint_acknowledgement": "Bank complaint acknowledgement",
    "supporting_document": "Supporting document",
}


CASE_PREFIX = "RT"
CASE_START = 10482


def next_case_id(db: Session) -> str:
    """The next free case number.

    Counting rows and adding an offset breaks the moment anything is deleted —
    a demo reset drops the count, and the next case collides with one another
    account is already holding. `case_id` is globally unique, so this walks up
    from the highest number actually in use instead.
    """
    highest = CASE_START - 1
    for (existing,) in db.execute(select(Incident.case_id)):
        _, _, digits = (existing or "").rpartition("-")
        if digits.isdigit():
            highest = max(highest, int(digits))

    candidate = highest + 1
    taken = {row[0] for row in db.execute(select(Incident.case_id))}
    while f"{CASE_PREFIX}-{candidate}" in taken:
        candidate += 1
    return f"{CASE_PREFIX}-{candidate}"


def create_incident(
    db: Session,
    user: User,
    transaction: Transaction | None,
    refund: RefundRequest | None,
    risk_score: int,
    risk_level: str,
    summary: str | None = None,
    scam_message: str | None = None,
    title: str = "Suspected refund scam",
    potential_loss: float | None = None,
) -> Incident:
    incident = Incident(
        case_id=next_case_id(db),
        user_id=user.id,
        transaction_id=transaction.id if transaction else None,
        refund_request_id=refund.id if refund else None,
        title=title,
        summary=summary or default_summary(transaction, refund),
        status="OPEN",
        risk_level=risk_level,
        risk_score=risk_score,
        potential_loss=(
            potential_loss
            if potential_loss is not None
            else (refund.amount if refund else (transaction.amount if transaction else 0.0))
        ),
        suspect_handle=transaction.sender_handle if transaction else None,
        scam_message=scam_message or (refund.message if refund else None),
    )
    db.add(incident)
    db.flush()
    return incident


def default_summary(transaction: Transaction | None, refund: RefundRequest | None) -> str:
    if not transaction:
        return "A suspicious refund sequence was recorded on this account."
    amount = f"Rs {transaction.amount:,.0f}"
    base = (
        f"A payment of {amount} was received from {transaction.sender_handle}, an account with no "
        "prior history on this profile."
    )
    if refund:
        mins = max(round(refund.seconds_since_payment / 60), 1)
        if not refund.destination_matches_sender:
            base += (
                f" About {mins} minute(s) later a refund was requested to {refund.refund_destination}, "
                "which is not the account the money came from."
            )
        else:
            base += f" About {mins} minute(s) later a refund of the same amount was requested."
    base += " The sequence matches the pattern of a refund-abuse scam."
    return base


def add_event(
    db: Session,
    incident: Incident,
    title: str,
    detail: str | None = None,
    source: str = "SYSTEM",
    severity: str = "info",
    occurred_at: datetime | None = None,
) -> IncidentEvent:
    event = IncidentEvent(
        incident_id=incident.id,
        occurred_at=occurred_at or utcnow(),
        source=source,
        title=title,
        detail=detail,
        severity=severity,
    )
    db.add(event)
    return event


def build_timeline_from_transaction(
    db: Session, incident: Incident, transaction: Transaction, refund: RefundRequest | None
) -> None:
    """Fold transaction events, the refund and system actions into one ordered timeline."""
    for ev in sorted(transaction.events, key=lambda e: e.occurred_at):
        add_event(
            db,
            incident,
            ev.title,
            ev.detail,
            source="TRANSACTION",
            severity=ev.severity,
            occurred_at=ev.occurred_at,
        )
    if refund is not None:
        base = transaction.created_at + timedelta(seconds=refund.seconds_since_payment)
        add_event(
            db,
            incident,
            f"Refund requested to {refund.refund_destination}",
            (
                "Destination does not match the original sender."
                if not refund.destination_matches_sender
                else "Destination matches the original sender."
            ),
            source="REFUND",
            severity="warning" if not refund.destination_matches_sender else "info",
            occurred_at=base,
        )
    add_event(
        db,
        incident,
        "Retrace flagged a high-risk refund pattern",
        f"Combined risk score {incident.risk_score}/100 ({incident.risk_level}).",
        severity="critical" if incident.risk_level == "CRITICAL" else "warning",
    )


def seed_evidence_placeholders(db: Session, incident: Incident, present: list[str]) -> None:
    """Create checklist rows so the vault shows what is still missing."""
    for kind in REQUIRED_EVIDENCE:
        db.add(
            Evidence(
                user_id=incident.user_id,
                incident_id=incident.id,
                label=EVIDENCE_LABELS.get(kind, kind.replace("_", " ").title()),
                category=_category_for(kind),
                evidence_type=kind,
                placeholder=kind not in present,
                description=None if kind in present else "Not collected yet.",
                size_bytes=0,
            )
        )


def _category_for(kind: str) -> str:
    if kind in {"bank_statement", "original_transaction", "refund_transaction", "payment_receipt"}:
        return "FINANCIAL"
    if kind in {"whatsapp", "sms", "call_log", "call_recording"}:
        return "COMMUNICATION"
    if kind in {"bank_complaint", "bank_email", "complaint_acknowledgement"}:
        return "BANK"
    return "OTHER"


def completeness(db: Session, incident_id: int | None, user_id: int) -> dict:
    stmt = select(Evidence).where(Evidence.user_id == user_id)
    if incident_id is not None:
        stmt = stmt.where(Evidence.incident_id == incident_id)
    items = db.scalars(stmt).all()

    collected = {e.evidence_type for e in items if not e.placeholder}
    present = [k for k in REQUIRED_EVIDENCE if k in collected]
    missing = [k for k in REQUIRED_EVIDENCE if k not in collected]
    percent = round(len(present) / len(REQUIRED_EVIDENCE) * 100) if REQUIRED_EVIDENCE else 0
    return {
        "percent": percent,
        "present": [EVIDENCE_LABELS.get(k, k) for k in present],
        "missing": [EVIDENCE_LABELS.get(k, k) for k in missing],
        "total_files": sum(1 for e in items if not e.placeholder),
    }


def enable_safe_mode(db: Session, user: User, reason: str | None = None) -> None:
    user.safe_mode_enabled = True
    user.safe_mode_activated_at = utcnow()
    db.add(
        Alert(
            user_id=user.id,
            title="Safe Mode is on",
            body=reason or "Extra checks now apply to new beneficiaries and high-risk transfers.",
            severity="HIGH",
        )
    )


def connected_transaction_count(db: Session, incident: Incident) -> int:
    if not incident.suspect_handle:
        return 0
    return int(
        db.scalar(
            select(func.count(Transaction.id)).where(
                Transaction.sender_handle == incident.suspect_handle
            )
        )
        or 0
    )

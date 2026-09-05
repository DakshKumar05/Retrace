from __future__ import annotations

import secrets
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.api.deps import current_user
from app.database import get_db
from app.models import Alert, Incident, RefundRequest, RiskAssessment, Transaction, User
from app.schemas import (
    AlertOut,
    DashboardResponse,
    RefundRequestOut,
    RiskAssessmentOut,
    TransactionCreate,
    TransactionDetailOut,
    TransactionOut,
)
from app.services import incident_service

router = APIRouter(prefix="/api", tags=["transactions"])

FILTERS = {
    "all": None,
    "safe": ["SAFE"],
    "suspicious": ["SUSPICIOUS"],
    "high_risk": ["HIGH_RISK"],
}


@router.get("/transactions", response_model=list[TransactionOut])
def list_transactions(
    filter: str = Query("all", pattern="^(all|safe|suspicious|high_risk)$"),
    search: str | None = Query(None, max_length=120),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> list[TransactionOut]:
    stmt = select(Transaction).where(Transaction.user_id == user.id)
    labels = FILTERS.get(filter)
    if labels:
        stmt = stmt.where(Transaction.label.in_(labels))
    if search:
        term = f"%{search.strip()}%"
        stmt = stmt.where(
            or_(
                Transaction.reference.ilike(term),
                Transaction.sender_handle.ilike(term),
                Transaction.receiver_handle.ilike(term),
            )
        )
    rows = db.scalars(
        stmt.order_by(Transaction.created_at.desc()).limit(limit).offset(offset)
    ).all()
    return [TransactionOut.model_validate(r) for r in rows]


@router.get("/transactions/{reference}", response_model=TransactionDetailOut)
def get_transaction(
    reference: str, user: User = Depends(current_user), db: Session = Depends(get_db)
) -> TransactionDetailOut:
    tx = db.scalar(
        select(Transaction).where(
            Transaction.reference == reference, Transaction.user_id == user.id
        )
    )
    if tx is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="No transaction with that reference.")

    assessment = (
        db.query(RiskAssessment)
        .filter(RiskAssessment.transaction_id == tx.id)
        .order_by(RiskAssessment.created_at.desc())
        .first()
    )
    detail = TransactionDetailOut.model_validate(tx)
    detail.latest_assessment = (
        RiskAssessmentOut.model_validate(assessment) if assessment else None
    )
    return detail


@router.post("/transactions", response_model=TransactionOut, status_code=status.HTTP_201_CREATED)
def create_transaction(
    payload: TransactionCreate, user: User = Depends(current_user), db: Session = Depends(get_db)
) -> TransactionOut:
    tx = Transaction(
        reference=f"TX{secrets.randbelow(90000) + 10000}",
        user_id=user.id,
        direction=payload.direction,
        amount=payload.amount,
        sender_handle=payload.sender_handle,
        receiver_handle=user.upi_id if payload.direction == "credit" else payload.sender_handle,
        payment_method=payload.payment_method,
        status="COMPLETED",
        label="SAFE",
        sender_known=payload.sender_known,
        sender_account_age_days=payload.sender_account_age_days,
        note=payload.note,
    )
    db.add(tx)
    db.commit()
    db.refresh(tx)
    return TransactionOut.model_validate(tx)


@router.get("/dashboard", response_model=DashboardResponse)
def dashboard(user: User = Depends(current_user), db: Session = Depends(get_db)) -> DashboardResponse:
    recent = db.scalars(
        select(Transaction)
        .where(Transaction.user_id == user.id)
        .order_by(Transaction.created_at.desc())
        .limit(6)
    ).all()
    alerts = db.scalars(
        select(Alert).where(Alert.user_id == user.id).order_by(Alert.created_at.desc()).limit(5)
    ).all()
    pending = db.scalars(
        select(RefundRequest)
        .where(RefundRequest.user_id == user.id, RefundRequest.status.in_(["PENDING", "BLOCKED"]))
        .order_by(RefundRequest.created_at.desc())
        .limit(5)
    ).all()

    total_value = float(
        db.scalar(
            select(func.coalesce(func.sum(Transaction.amount), 0.0)).where(
                Transaction.user_id == user.id, Transaction.direction == "credit"
            )
        )
        or 0.0
    )
    risk_alerts = int(
        db.scalar(
            select(func.count(Alert.id)).where(
                Alert.user_id == user.id, Alert.severity.in_(["HIGH", "CRITICAL"])
            )
        )
        or 0
    )
    open_incidents = int(
        db.scalar(
            select(func.count(Incident.id)).where(
                Incident.user_id == user.id,
                Incident.status.in_(["OPEN", "UNDER_REVIEW", "REPORT_READY"]),
            )
        )
        or 0
    )

    latest_incident = db.scalar(
        select(Incident).where(Incident.user_id == user.id).order_by(Incident.created_at.desc())
    )
    stats = (
        incident_service.completeness(db, latest_incident.id, user.id) if latest_incident else None
    )

    return DashboardResponse(
        greeting=_greeting(),
        protection_active=True,
        safe_mode_enabled=user.safe_mode_enabled,
        total_transaction_value=total_value,
        protected_funds=user.protected_balance,
        risk_alerts=risk_alerts,
        open_incidents=open_incidents,
        recent_transactions=[TransactionOut.model_validate(t) for t in recent],
        recent_alerts=[AlertOut.model_validate(a) for a in alerts],
        pending_refund_requests=[RefundRequestOut.model_validate(r) for r in pending],
        evidence_completeness=stats["percent"] if stats else None,
    )


def _greeting() -> str:
    hour = datetime.now(timezone.utc).astimezone().hour
    if hour < 12:
        return "Good morning"
    if hour < 17:
        return "Good afternoon"
    return "Good evening"

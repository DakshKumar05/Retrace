from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import current_user, protection_for
from app.database import get_db
from app.models import Alert, RefundRequest, Transaction, User, utcnow
from app.schemas import (
    AlertOut,
    ProtectionActivateRequest,
    ProtectionSettingOut,
    ProtectionSettingUpdate,
    RefundAnalysisRequest,
    RefundRequestOut,
    SafeModeRequest,
    SafeRefundRequest,
    SafeRefundResponse,
    UnsafeRefundRequest,
    UserOut,
)
from app.services import incident_service, refund_service

router = APIRouter(prefix="/api", tags=["refunds"])


def _load_refund(db: Session, user: User, refund_id: int) -> tuple[RefundRequest, Transaction]:
    refund = db.scalar(
        select(RefundRequest).where(RefundRequest.id == refund_id, RefundRequest.user_id == user.id)
    )
    if refund is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="No refund request with that id.")
    tx = db.get(Transaction, refund.transaction_id)
    if tx is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="The original transaction is missing.")
    return refund, tx


@router.get("/refunds", response_model=list[RefundRequestOut])
def list_refunds(
    user: User = Depends(current_user), db: Session = Depends(get_db)
) -> list[RefundRequestOut]:
    rows = db.scalars(
        select(RefundRequest)
        .where(RefundRequest.user_id == user.id)
        .order_by(RefundRequest.created_at.desc())
    ).all()
    return [RefundRequestOut.model_validate(r) for r in rows]


@router.post("/refunds/analyze")
def analyze_refund(
    payload: RefundAnalysisRequest,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    from app.api.risk import _analyse

    return _analyse(payload, user, db)


@router.post("/refunds/safe", response_model=SafeRefundResponse)
def safe_refund(
    payload: SafeRefundRequest, user: User = Depends(current_user), db: Session = Depends(get_db)
) -> SafeRefundResponse:
    """Send the money back down the original payment rail, never to a new handle."""
    refund, tx = _load_refund(db, user, payload.refund_request_id)
    if refund.status == "SAFE_REFUND_INITIATED":
        raise HTTPException(status.HTTP_409_CONFLICT, detail="A safe refund is already in progress.")

    result = refund_service.initiate_safe_refund(db, refund, tx)
    refund_service.settle_safe_refund(db, user, refund, tx)
    db.commit()
    return SafeRefundResponse(**result)


@router.post("/refunds/manual", response_model=RefundRequestOut)
def manual_refund(
    payload: UnsafeRefundRequest, user: User = Depends(current_user), db: Session = Depends(get_db)
) -> RefundRequestOut:
    """Record that the user chose to transfer manually, and open an incident if it was risky."""
    refund, tx = _load_refund(db, user, payload.refund_request_id)
    if not payload.confirm:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail="Confirm that you understand the risk before recording a manual transfer.",
        )

    refund.status = "MANUAL_TRANSFER"
    refund_service.settle_manual_transfer(db, user, refund, tx)
    if refund.risk_level in {"HIGH", "CRITICAL"}:
        incident = incident_service.create_incident(
            db, user, tx, refund, refund.risk_score, refund.risk_level, scam_message=refund.message
        )
        incident_service.build_timeline_from_transaction(db, incident, tx, refund)
        incident_service.enable_safe_mode(db, user, "Turned on after a high-risk manual transfer.")
        incident_service.seed_evidence_placeholders(
            db, incident, present=["bank_statement", "original_transaction", "refund_transaction"]
        )
    db.commit()
    db.refresh(refund)
    return RefundRequestOut.model_validate(refund)


@router.post("/refunds/{refund_id}/cancel", response_model=RefundRequestOut)
def cancel_refund(
    refund_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)
) -> RefundRequestOut:
    refund, _ = _load_refund(db, user, refund_id)
    refund.status = "CANCELLED"
    db.commit()
    db.refresh(refund)
    return RefundRequestOut.model_validate(refund)


# ---------------------------------------------------------------- safe mode
@router.post("/safe-mode", response_model=UserOut)
def set_safe_mode(
    payload: SafeModeRequest, user: User = Depends(current_user), db: Session = Depends(get_db)
) -> UserOut:
    """Turn the simulated protection state on or off. No real bank control is involved."""
    user.safe_mode_enabled = payload.enabled
    user.safe_mode_activated_at = utcnow() if payload.enabled else None
    db.add(
        Alert(
            user_id=user.id,
            title="Safe Mode is on" if payload.enabled else "Safe Mode is off",
            body=payload.reason
            or (
                "Extra checks now apply to new beneficiaries and high-risk transfers."
                if payload.enabled
                else "Your account is back to normal checks."
            ),
            severity="HIGH" if payload.enabled else "LOW",
        )
    )
    db.commit()
    db.refresh(user)
    return UserOut.model_validate(user)


@router.get("/alerts", response_model=list[AlertOut])
def list_alerts(user: User = Depends(current_user), db: Session = Depends(get_db)) -> list[AlertOut]:
    rows = db.scalars(
        select(Alert).where(Alert.user_id == user.id).order_by(Alert.created_at.desc()).limit(40)
    ).all()
    return [AlertOut.model_validate(a) for a in rows]


# ---------------------------------------------------------------- emergency protection
@router.get("/protection", response_model=ProtectionSettingOut)
def get_protection(
    user: User = Depends(current_user), db: Session = Depends(get_db)
) -> ProtectionSettingOut:
    setting = protection_for(db, user)
    db.commit()
    return ProtectionSettingOut.model_validate(setting)


@router.patch("/protection", response_model=ProtectionSettingOut)
def update_protection(
    payload: ProtectionSettingUpdate,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> ProtectionSettingOut:
    setting = protection_for(db, user)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(setting, field, value)
    db.commit()
    db.refresh(setting)
    return ProtectionSettingOut.model_validate(setting)


@router.post("/protection/activate", response_model=ProtectionSettingOut)
def activate_protection(
    payload: ProtectionActivateRequest,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> ProtectionSettingOut:
    """Move a simulated balance into a protected state. No real funds are touched."""
    setting = protection_for(db, user)
    if not setting.enabled:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail="Turn on emergency protection before using it.",
        )

    amount = payload.amount if payload.amount is not None else round(user.balance * 0.5, 2)
    amount = min(amount, user.balance)
    if amount <= 0:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="There is no balance to protect.")

    user.balance -= amount
    user.protected_balance += amount
    setting.protection_active = True
    setting.activated_at = utcnow()
    db.add(
        Alert(
            user_id=user.id,
            title="Funds moved to a protected state",
            body=(
                f"Rs {amount:,.0f} is now held back from outgoing transfers in this demo. "
                "Nothing has moved in your real bank account."
            ),
            severity="HIGH",
        )
    )
    db.commit()
    db.refresh(setting)
    return ProtectionSettingOut.model_validate(setting)


@router.post("/protection/release", response_model=ProtectionSettingOut)
def release_protection(
    user: User = Depends(current_user), db: Session = Depends(get_db)
) -> ProtectionSettingOut:
    setting = protection_for(db, user)
    user.balance += user.protected_balance
    user.protected_balance = 0.0
    setting.protection_active = False
    setting.activated_at = None
    db.commit()
    db.refresh(setting)
    return ProtectionSettingOut.model_validate(setting)

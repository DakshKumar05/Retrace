"""Build the scam yourself, one step at a time.

Open an account, fund it, choose who pays you and what they say, then decide.
The risk engine is the same one every other screen uses; only the inputs change.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import current_user
from app.database import get_db
from app.models import RefundRequest, Transaction, User
from app.schemas import (
    IncidentOut,
    RefundAnalysisResponse,
    RefundRequestOut,
    LabAccountRequest,
    LabAccountResponse,
    LabBatchRequest,
    LabBatchResponse,
    LabBatchRow,
    LabFundsRequest,
    LabFundsResponse,
    LabResolveRequest,
    LabResolveResponse,
    LabScamRequest,
    LabScamResponse,
    ScamPreset,
    TransactionOut,
    UserOut,
)
from app.services import lab_service
from app.services.security import create_access_token

router = APIRouter(prefix="/api/lab", tags=["lab"])


@router.get("/scam-presets", response_model=list[ScamPreset])
def scam_presets() -> list[ScamPreset]:
    """Ready-made scam wording, so nobody has to invent it mid-demo."""
    return [ScamPreset(**preset) for preset in lab_service.SCAM_PRESETS]


@router.post("/account", response_model=LabAccountResponse, status_code=status.HTTP_201_CREATED)
def create_account(
    payload: LabAccountRequest, db: Session = Depends(get_db)
) -> LabAccountResponse:
    """Open an empty account under a name you choose, and sign in as it."""
    user, password = lab_service.create_account(
        db,
        full_name=payload.full_name,
        upi_handle=payload.upi_handle,
        opening_balance=payload.opening_balance,
        as_admin=payload.as_admin,
    )
    token, expires_in = create_access_token(user.email, user.role)
    return LabAccountResponse(
        access_token=token,
        expires_in=expires_in,
        user=UserOut.model_validate(user),
        password=password,
    )


@router.post("/funds", response_model=LabFundsResponse)
def add_funds(
    payload: LabFundsRequest,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> LabFundsResponse:
    """Put money in, so there is something for the scam to take."""
    transaction = lab_service.add_funds(
        db, user, amount=payload.amount, from_handle=payload.from_handle, note=payload.note
    )
    return LabFundsResponse(
        user=UserOut.model_validate(user), transaction=TransactionOut.model_validate(transaction)
    )


@router.post("/scam", response_model=LabScamResponse)
def deliver_scam(
    payload: LabScamRequest,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> LabScamResponse:
    """The payment lands, the message arrives, and the refund gets scored."""
    result = lab_service.deliver_scam(
        db, user,
        amount=payload.amount,
        sender_handle=payload.sender_handle,
        refund_destination=payload.refund_destination,
        message=payload.message,
        minutes_since_payment=payload.minutes_since_payment,
    )
    verdict = result["verdict"]
    analysis = RefundAnalysisResponse(
        transaction_id=result["transaction"].reference,
        destination_matches_sender=result["destination_matches_sender"],
        refund_request_id=result["refund_request"].id,
        **verdict.as_dict(),
    )
    return LabScamResponse(
        user=UserOut.model_validate(user),
        transaction=TransactionOut.model_validate(result["transaction"]),
        refund_request=RefundRequestOut.model_validate(result["refund_request"]),
        analysis=analysis,
    )


@router.post("/batch", response_model=LabBatchResponse)
def generate_batch(
    payload: LabBatchRequest,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> LabBatchResponse:
    """Send a stream of randomised refund requests in and score every one.

    The mix is roughly 60% scam, 20% borderline and 20% genuine, so the spread
    of scores shows the engine separating cases rather than flagging everything.
    """
    rows = lab_service.generate_batch(db, user, payload.count)
    return LabBatchResponse(
        user=UserOut.model_validate(user), rows=[LabBatchRow(**row) for row in rows]
    )


@router.post("/resolve", response_model=LabResolveResponse)
def resolve(
    payload: LabResolveRequest,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> LabResolveResponse:
    """Decide what happens: send it back safely, or transfer it and find out."""
    refund = db.scalar(
        select(RefundRequest).where(
            RefundRequest.id == payload.refund_request_id, RefundRequest.user_id == user.id
        )
    )
    if refund is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="No refund request with that id.")
    if refund.status in {"SAFE_REFUND_INITIATED", "MANUAL_TRANSFER"}:
        raise HTTPException(status.HTTP_409_CONFLICT, detail="This refund has already been resolved.")

    transaction = db.get(Transaction, refund.transaction_id)
    if transaction is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="The original transaction is missing.")

    result = lab_service.resolve(db, user, refund, transaction, payload.action)
    return LabResolveResponse(
        user=UserOut.model_validate(result["user"]),
        refund_request=RefundRequestOut.model_validate(result["refund_request"]),
        incident=IncidentOut.model_validate(result["incident"]) if result["incident"] else None,
        events=result["events"],
        loss=result["loss"],
    )

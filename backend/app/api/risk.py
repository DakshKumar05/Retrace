from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import current_user
from app.database import get_db
from app.ml import model as ml_model
from app.models import Transaction, User
from app.nlp import analyze_message
from app.schemas import (
    MessageAnalysisRequest,
    MessageAnalysisResponse,
    RefundAnalysisRequest,
    RefundAnalysisResponse,
)
from app.services import refund_service

router = APIRouter(prefix="/api/risk", tags=["risk"])


def _analyse(payload: RefundAnalysisRequest, user: User, db: Session) -> RefundAnalysisResponse:
    tx = db.scalar(
        select(Transaction).where(
            Transaction.reference == payload.transaction_id, Transaction.user_id == user.id
        )
    )
    ctx = refund_service.build_context(
        db,
        user,
        tx,
        refund_amount=payload.refund_amount,
        original_sender=payload.original_sender,
        refund_destination=payload.refund_destination,
        seconds_since_payment=payload.time_since_payment,
        message=payload.message,
    )
    verdict = refund_service.analyse(db, ctx)

    refund_request_id = None
    if payload.persist and tx is not None:
        existing = next(
            (
                r
                for r in tx.refund_requests
                if r.refund_destination.lower() == payload.refund_destination.lower()
                and r.status in {"PENDING", "BLOCKED"}
            ),
            None,
        )
        if existing is None:
            existing = refund_service.create_refund_request(
                db, user, tx, payload.refund_destination, verdict,
                payload.time_since_payment, message=payload.message,
            )
            if verdict.risk_level in {"HIGH", "CRITICAL"}:
                refund_service.raise_alert(db, user, verdict, tx)
        else:
            existing.risk_score = verdict.risk_score
            existing.safety_score = verdict.safety_score
            existing.risk_level = verdict.risk_level
            existing.recommendation = verdict.recommendation
        refund_service.persist_assessment(db, user, verdict, tx, existing)
        db.commit()
        refund_request_id = existing.id

    data = verdict.as_dict()
    return RefundAnalysisResponse(
        transaction_id=payload.transaction_id,
        destination_matches_sender=ctx.normalised_destination() == ctx.normalised_sender(),
        refund_request_id=refund_request_id,
        **data,
    )


@router.post("/analyze-refund", response_model=RefundAnalysisResponse)
def analyze_refund(
    payload: RefundAnalysisRequest,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> RefundAnalysisResponse:
    """Answer the product's core question: is it safe for this user to refund?"""
    return _analyse(payload, user, db)


@router.post("/analyze", response_model=RefundAnalysisResponse)
def analyze(
    payload: RefundAnalysisRequest,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> RefundAnalysisResponse:
    """Alias kept for generic risk analysis calls."""
    return _analyse(payload, user, db)


@router.post("/analyze-message", response_model=MessageAnalysisResponse)
def analyze_message_route(
    payload: MessageAnalysisRequest, user: User = Depends(current_user)
) -> MessageAnalysisResponse:
    result = analyze_message(payload.message)
    return MessageAnalysisResponse(**result.as_dict())


@router.get("/model-info")
def model_info(user: User = Depends(current_user)) -> dict:
    return ml_model.metrics()

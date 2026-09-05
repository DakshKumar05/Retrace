"""Razorpay Test Mode payment intake and webhook handling.

A credit that arrives through Checkout carries a real ``pay_...`` id, which is
what later lets the safe refund go back to source through Razorpay instead of
being recorded as a simulation.
"""
from __future__ import annotations

import logging
import secrets

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import current_user
from app.config import settings
from app.database import get_db
from app.models import Alert, RefundRequest, Transaction, TransactionEvent, User
from app.schemas import (
    CreateOrderRequest,
    CreateOrderResponse,
    PaymentsConfigOut,
    TransactionOut,
    VerifyPaymentRequest,
    VerifyPaymentResponse,
)
from app.services import razorpay_client

log = logging.getLogger("retrace.payments")

router = APIRouter(prefix="/api/payments", tags=["payments"])
webhook_router = APIRouter(prefix="/api/webhooks", tags=["payments"])


def _require_test_mode() -> None:
    if not razorpay_client.enabled():
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "Razorpay Test Mode is not configured. Set RAZORPAY_KEY_ID and "
                "RAZORPAY_KEY_SECRET to test keys, or use the simulated flow."
            ),
        )


@router.get("/config", response_model=PaymentsConfigOut)
def payments_config() -> PaymentsConfigOut:
    """Public, key-id only. The secret never leaves the server."""
    enabled = razorpay_client.enabled()
    return PaymentsConfigOut(
        enabled=enabled,
        mode="RAZORPAY_TEST_MODE" if enabled else "SIMULATED",
        key_id=settings.razorpay_key_id if enabled else None,
        webhook_configured=bool(settings.razorpay_webhook_secret),
    )


@router.post("/order", response_model=CreateOrderResponse)
def create_order(
    payload: CreateOrderRequest, user: User = Depends(current_user)
) -> CreateOrderResponse:
    """Open a test-mode order so Checkout can produce a genuine payment id."""
    _require_test_mode()
    receipt = f"rs_{secrets.randbelow(900000) + 100000}"
    try:
        order = razorpay_client.create_order(
            payload.amount,
            receipt,
            notes={
                "purpose": "Retrace demo inbound credit",
                "user_id": str(user.id),
                "claimed_sender": payload.sender_handle,
            },
        )
    except razorpay_client.RazorpayError as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc

    return CreateOrderResponse(
        order_id=order["id"],
        amount=payload.amount,
        currency=order.get("currency", "INR"),
        key_id=settings.razorpay_key_id or "",
        receipt=receipt,
    )


@router.post("/verify", response_model=VerifyPaymentResponse)
def verify_payment(
    payload: VerifyPaymentRequest,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> VerifyPaymentResponse:
    """Check the Checkout signature, then record the credit as a transaction."""
    _require_test_mode()

    if not razorpay_client.verify_checkout_signature(
        payload.razorpay_order_id, payload.razorpay_payment_id, payload.razorpay_signature
    ):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail="That payment signature did not verify. Nothing has been recorded.",
        )

    existing = db.scalar(
        select(Transaction).where(Transaction.provider_payment_id == payload.razorpay_payment_id)
    )
    if existing is not None:
        return VerifyPaymentResponse(
            verified=True,
            transaction=TransactionOut.model_validate(existing),
            message="This payment was already recorded.",
        )

    try:
        payment = razorpay_client.fetch_payment(payload.razorpay_payment_id)
    except razorpay_client.RazorpayError as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc

    amount = float(payment.get("amount", 0)) / 100.0
    sender = payment.get("vpa") or payload.sender_handle

    transaction = Transaction(
        reference=f"TX{secrets.randbelow(90000) + 10000}",
        user_id=user.id,
        direction="credit",
        amount=amount,
        currency=payment.get("currency", "INR"),
        sender_handle=sender,
        receiver_handle=user.upi_id,
        payment_method=(payment.get("method") or "UPI").upper(),
        status="COMPLETED",
        label="SUSPICIOUS",
        sender_known=False,
        sender_account_age_days=6,
        sender_prior_reports=0,
        sender_suspicious_history=False,
        note="Received through Razorpay Test Mode. No live funds are involved.",
        is_demo=True,
        provider_order_id=payload.razorpay_order_id,
        provider_payment_id=payload.razorpay_payment_id,
    )
    db.add(transaction)
    db.flush()

    db.add(
        TransactionEvent(
            transaction_id=transaction.id,
            kind="payment_received",
            title=f"Rs {amount:,.0f} received",
            detail=(
                f"Razorpay Test Mode payment {payload.razorpay_payment_id}, signature verified."
            ),
            severity="info",
        )
    )
    db.commit()
    db.refresh(transaction)

    return VerifyPaymentResponse(
        verified=True,
        transaction=TransactionOut.model_validate(transaction),
        message=(
            "Payment verified through Razorpay Test Mode. A refund on this payment can only "
            "go back to the account that paid."
        ),
    )


@webhook_router.post("/razorpay", status_code=status.HTTP_200_OK)
async def razorpay_webhook(
    request: Request,
    x_razorpay_signature: str = Header(default=""),
    db: Session = Depends(get_db),
) -> dict:
    """Signature-verified provider callbacks. Unsigned requests are rejected."""
    if not settings.razorpay_webhook_secret:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE, detail="No webhook secret is configured."
        )

    raw = await request.body()
    if not razorpay_client.verify_webhook_signature(raw, x_razorpay_signature):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Signature verification failed.")

    payload = await request.json()
    event = payload.get("event", "")
    entities = payload.get("payload", {})

    if event.startswith("refund."):
        refund_entity = entities.get("refund", {}).get("entity", {})
        _apply_refund_event(db, event, refund_entity)
    elif event == "payment.captured":
        payment_entity = entities.get("payment", {}).get("entity", {})
        _apply_payment_captured(db, payment_entity)

    db.commit()
    log.info("Razorpay webhook handled: %s", event)
    return {"status": "ok", "event": event}


def _apply_refund_event(db: Session, event: str, entity: dict) -> None:
    refund_id = entity.get("id")
    if not refund_id:
        return
    refund = db.scalar(select(RefundRequest).where(RefundRequest.provider_refund_id == refund_id))
    if refund is None:
        return

    provider_status = entity.get("status", "")
    refund.provider_status = provider_status.upper() or refund.provider_status
    if event == "refund.processed":
        refund.status = "SAFE_REFUND_COMPLETED"
        db.add(
            Alert(
                user_id=refund.user_id,
                transaction_id=refund.transaction_id,
                title="Safe refund completed",
                body=(
                    "Razorpay confirmed the refund was processed back to the original payment "
                    "method. The money could not be redirected anywhere else."
                ),
                severity="LOW",
            )
        )
    elif event == "refund.failed":
        refund.status = "SAFE_REFUND_FAILED"
        db.add(
            Alert(
                user_id=refund.user_id,
                transaction_id=refund.transaction_id,
                title="Safe refund failed",
                body="Razorpay reported the refund could not be processed. No money moved.",
                severity="HIGH",
            )
        )


def _apply_payment_captured(db: Session, entity: dict) -> None:
    payment_id = entity.get("id")
    if not payment_id:
        return
    transaction = db.scalar(
        select(Transaction).where(Transaction.provider_payment_id == payment_id)
    )
    if transaction is None:
        return
    transaction.status = "COMPLETED"
    db.add(
        TransactionEvent(
            transaction_id=transaction.id,
            kind="payment_captured",
            title="Payment captured",
            detail=f"Razorpay confirmed capture of {payment_id}.",
            severity="info",
        )
    )

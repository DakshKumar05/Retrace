from __future__ import annotations

from pydantic import BaseModel, Field

from app.schemas.core import TransactionOut


class PaymentsConfigOut(BaseModel):
    """What the frontend needs to decide between Checkout and the simulated flow."""

    enabled: bool
    mode: str
    key_id: str | None = None
    webhook_configured: bool = False


class CreateOrderRequest(BaseModel):
    amount: float = Field(gt=0, le=100000)
    sender_handle: str = Field(default="unknown@upi", max_length=120)


class CreateOrderResponse(BaseModel):
    order_id: str
    amount: float
    currency: str
    key_id: str
    receipt: str


class VerifyPaymentRequest(BaseModel):
    razorpay_order_id: str = Field(max_length=60)
    razorpay_payment_id: str = Field(max_length=60)
    razorpay_signature: str = Field(max_length=256)
    sender_handle: str = Field(default="unknown@upi", max_length=120)


class VerifyPaymentResponse(BaseModel):
    verified: bool
    transaction: TransactionOut
    message: str


class RefundStatusOut(BaseModel):
    refund_id: str
    status: str
    amount: float
    speed_processed: str | None = None
    mode: str

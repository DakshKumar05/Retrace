from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.core import (
    RefundAnalysisResponse,
    RefundRequestOut,
    TokenResponse,
    TransactionOut,
    UserOut,
)
from app.schemas.incident import IncidentOut


class LabAccountRequest(BaseModel):
    full_name: str = Field(min_length=2, max_length=120)
    upi_handle: str | None = Field(default=None, max_length=120)
    opening_balance: float = Field(default=0, ge=0, le=10_000_000)
    as_admin: bool = False


class LabAccountResponse(TokenResponse):
    """The generated password is shown once so the account can be revisited."""

    password: str


class LabFundsRequest(BaseModel):
    amount: float = Field(gt=0, le=10_000_000)
    from_handle: str = Field(default="priya.sharma@okaxis", min_length=3, max_length=120)
    note: str | None = Field(default=None, max_length=200)


class LabFundsResponse(BaseModel):
    user: UserOut
    transaction: TransactionOut


class ScamPreset(BaseModel):
    id: str
    label: str
    sender_handle: str
    refund_destination: str
    message: str


class LabScamRequest(BaseModel):
    amount: float = Field(gt=0, le=10_000_000)
    sender_handle: str = Field(min_length=3, max_length=120)
    refund_destination: str = Field(min_length=3, max_length=120)
    message: str = Field(min_length=1, max_length=5000)
    minutes_since_payment: int = Field(default=4, ge=0, le=10_080)


class LabScamResponse(BaseModel):
    user: UserOut
    transaction: TransactionOut
    refund_request: RefundRequestOut
    analysis: RefundAnalysisResponse


class LabResolveRequest(BaseModel):
    refund_request_id: int
    action: Literal["safe", "manual"]


class LabResolveResponse(BaseModel):
    user: UserOut
    refund_request: RefundRequestOut
    incident: IncidentOut | None = None
    events: list[str]
    loss: float


class LabBatchRequest(BaseModel):
    count: int = Field(default=8, ge=1, le=25)


class LabBatchRow(BaseModel):
    kind: Literal["scam", "borderline", "genuine"]
    reference: str
    refund_request_id: int
    amount: float
    sender_handle: str
    refund_destination: str
    minutes_since_payment: int
    message: str
    risk_score: int
    safety_score: int
    risk_level: str
    recommendation: str
    top_reason: str


class LabBatchResponse(BaseModel):
    user: UserOut
    rows: list[LabBatchRow]

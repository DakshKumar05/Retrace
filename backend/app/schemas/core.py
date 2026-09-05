from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------- auth
class RegisterRequest(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=2, max_length=120)
    password: str = Field(min_length=8, max_length=128)

    @field_validator("password")
    @classmethod
    def strength(cls, v: str) -> str:
        if v.isalpha() or v.isdigit():
            raise ValueError("Use a password with both letters and numbers.")
        return v


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class UserOut(ORMModel):
    id: int
    email: EmailStr
    full_name: str
    role: str
    upi_id: str
    balance: float
    protected_balance: float
    safe_mode_enabled: bool
    safe_mode_activated_at: datetime | None = None
    created_at: datetime


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserOut


# ---------------------------------------------------------------- transactions
class TransactionEventOut(ORMModel):
    id: int
    occurred_at: datetime
    kind: str
    title: str
    detail: str | None = None
    severity: str


class TransactionOut(ORMModel):
    id: int
    reference: str
    direction: str
    amount: float
    currency: str
    sender_handle: str
    receiver_handle: str
    payment_method: str
    status: str
    label: str
    risk_score: int
    sender_known: bool
    sender_account_age_days: int
    sender_suspicious_history: bool
    sender_prior_reports: int
    refund_requested: bool
    note: str | None = None
    created_at: datetime


class TransactionDetailOut(TransactionOut):
    events: list[TransactionEventOut] = []
    refund_requests: list["RefundRequestOut"] = []
    latest_assessment: "RiskAssessmentOut | None" = None


class TransactionCreate(BaseModel):
    amount: float = Field(gt=0, le=10_000_000)
    sender_handle: str = Field(min_length=3, max_length=120)
    direction: Literal["credit", "debit"] = "credit"
    payment_method: str = Field(default="UPI", max_length=30)
    note: str | None = Field(default=None, max_length=500)
    sender_known: bool = True
    sender_account_age_days: int = Field(default=365, ge=0, le=20_000)


# ---------------------------------------------------------------- risk
class SignalOut(ORMModel):
    code: str
    label: str
    weight: int
    category: str = "RULE"
    detail: str | None = None


class RiskComponent(BaseModel):
    name: str
    value: int | None = None
    weight: float
    unit: str


class RefundAnalysisRequest(BaseModel):
    transaction_id: str = Field(min_length=1, max_length=32)
    refund_amount: float = Field(gt=0, le=10_000_000)
    original_sender: str = Field(min_length=3, max_length=120)
    refund_destination: str = Field(min_length=3, max_length=120)
    time_since_payment: int = Field(ge=0, le=31_536_000, description="Seconds since the credit")
    message: str | None = Field(default=None, max_length=5000)
    persist: bool = True


class RefundAnalysisResponse(BaseModel):
    transaction_id: str
    risk_score: int
    safety_score: int
    risk_level: str
    recommendation: str
    reasons: list[str]
    signals: list[SignalOut]
    components: list[RiskComponent]
    rule_score: int
    ml_probability: float | None = None
    message_score: int = 0
    network_score: int = 0
    ml_disclaimer: str
    destination_matches_sender: bool
    refund_request_id: int | None = None


class MessageAnalysisRequest(BaseModel):
    message: str = Field(min_length=1, max_length=5000)


class MessageAnalysisResponse(BaseModel):
    message_risk_score: int
    risk_level: str
    recommendation: str
    signals: list[SignalOut]
    matched_phrases: list[str]
    extracted_handles: list[str]
    word_count: int


class RiskAssessmentOut(ORMModel):
    id: int
    subject: str
    rule_score: int
    ml_probability: float
    message_score: int
    network_score: int
    risk_score: int
    safety_score: int
    risk_level: str
    recommendation: str
    created_at: datetime
    signals: list[SignalOut] = []


# ---------------------------------------------------------------- refunds
class RefundRequestOut(ORMModel):
    id: int
    reference: str
    transaction_id: int
    transaction_reference: str | None = None
    amount: float
    original_sender: str
    refund_destination: str
    destination_matches_sender: bool
    seconds_since_payment: int
    channel: str
    message: str | None = None
    status: str
    risk_score: int
    safety_score: int
    risk_level: str
    recommendation: str
    provider_refund_id: str | None = None
    provider_status: str | None = None
    created_at: datetime


class SafeRefundRequest(BaseModel):
    refund_request_id: int


class SafeRefundResponse(BaseModel):
    refund_id: str
    status: str
    amount: float
    destination: str
    mode: str
    message: str


class UnsafeRefundRequest(BaseModel):
    refund_request_id: int
    confirm: bool = False


class AlertOut(ORMModel):
    id: int
    title: str
    body: str | None = None
    severity: str
    read: bool
    created_at: datetime


class SafeModeRequest(BaseModel):
    enabled: bool
    reason: str | None = Field(default=None, max_length=200)


class ProtectionSettingOut(ORMModel):
    id: int
    enabled: bool
    account_last4: str
    nickname: str
    auto_activate_on_critical: bool
    protection_active: bool
    activated_at: datetime | None = None


class ProtectionSettingUpdate(BaseModel):
    enabled: bool | None = None
    account_last4: str | None = Field(default=None, pattern=r"^\d{4}$")
    nickname: str | None = Field(default=None, max_length=80)
    auto_activate_on_critical: bool | None = None


class ProtectionActivateRequest(BaseModel):
    amount: float | None = Field(default=None, gt=0)


class DashboardResponse(BaseModel):
    greeting: str
    protection_active: bool
    safe_mode_enabled: bool
    total_transaction_value: float
    protected_funds: float
    risk_alerts: int
    open_incidents: int
    recent_transactions: list[TransactionOut]
    recent_alerts: list[AlertOut]
    pending_refund_requests: list[RefundRequestOut]
    evidence_completeness: int | None = None


TransactionDetailOut.model_rebuild()

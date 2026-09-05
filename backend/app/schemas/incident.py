from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.schemas.core import ORMModel, RefundRequestOut, TransactionOut


class EvidenceOut(ORMModel):
    id: int
    incident_id: int | None = None
    label: str
    category: str
    evidence_type: str
    original_filename: str | None = None
    content_type: str | None = None
    size_bytes: int
    sha256: str | None = None
    placeholder: bool
    description: str | None = None
    uploaded_at: datetime


class EvidenceCompleteness(BaseModel):
    percent: int
    present: list[str]
    missing: list[str]
    total_files: int


class IncidentEventOut(ORMModel):
    id: int
    occurred_at: datetime
    source: str
    title: str
    detail: str | None = None
    severity: str


class IncidentOut(ORMModel):
    id: int
    case_id: str
    title: str
    summary: str | None = None
    status: str
    risk_level: str
    risk_score: int
    potential_loss: float
    suspect_handle: str | None = None
    bank_complaint_ref: str | None = None
    notes: str | None = None
    created_at: datetime
    updated_at: datetime


class IncidentDetailOut(IncidentOut):
    scam_message: str | None = None
    events: list[IncidentEventOut] = []
    evidence: list[EvidenceOut] = []
    completeness: EvidenceCompleteness = Field(
        default_factory=lambda: EvidenceCompleteness(
            percent=0, present=[], missing=[], total_files=0
        )
    )
    transaction: TransactionOut | None = None
    refund_request: RefundRequestOut | None = None
    connected_transactions: int = 0
    reports: list["ReportOut"] = []


class IncidentCreate(BaseModel):
    transaction_reference: str | None = None
    refund_request_id: int | None = None
    title: str = Field(default="Suspected refund scam", max_length=200)
    summary: str | None = Field(default=None, max_length=2000)
    potential_loss: float = Field(default=0, ge=0)
    suspect_handle: str | None = Field(default=None, max_length=120)
    scam_message: str | None = Field(default=None, max_length=5000)


class IncidentUpdate(BaseModel):
    status: Literal["OPEN", "UNDER_REVIEW", "REPORT_READY", "SUBMITTED", "RESOLVED"] | None = None
    notes: str | None = Field(default=None, max_length=4000)
    bank_complaint_ref: str | None = Field(default=None, max_length=80)
    summary: str | None = Field(default=None, max_length=2000)


class ReportOut(ORMModel):
    id: int
    incident_id: int
    reference: str
    pdf_filename: str
    package_filename: str | None = None
    evidence_count: int
    completeness: int
    generated_at: datetime


class ReportGenerateRequest(BaseModel):
    incident_id: int
    include_package: bool = True


# ---------------------------------------------------------------- admin
class AdminStatistics(BaseModel):
    total_transactions: int
    suspicious: int
    high_risk: int
    open_incidents: int
    protected_users: int
    total_value: float
    average_payment_to_refund_seconds: int
    transactions_over_time: list[dict[str, Any]]
    risk_distribution: list[dict[str, Any]]
    refund_scam_frequency: list[dict[str, Any]]
    top_signals: list[dict[str, Any]]
    network_size: dict[str, int]


class RiskFeedItem(BaseModel):
    timestamp: datetime
    reference: str
    amount: float
    risk_score: int
    risk_level: str
    sender_handle: str


# ---------------------------------------------------------------- simulation
class SimulationRequest(BaseModel):
    unsafe: bool = Field(default=False, description="Simulate the victim transferring manually")


class SimulationStep(BaseModel):
    step: int
    title: str
    detail: str
    at: datetime


class SimulationResponse(BaseModel):
    transaction: TransactionOut
    refund_request: RefundRequestOut
    analysis: dict
    steps: list[SimulationStep]
    incident: IncidentOut | None = None
    completeness: EvidenceCompleteness | None = None
    safe_mode_enabled: bool = False


IncidentDetailOut.model_rebuild()

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.session import Base
from app.models.user import utcnow

INCIDENT_STATUSES = ["OPEN", "UNDER_REVIEW", "REPORT_READY", "SUBMITTED", "RESOLVED"]

EVIDENCE_CATEGORIES = {
    "FINANCIAL": ["bank_statement", "original_transaction", "refund_transaction", "payment_receipt"],
    "COMMUNICATION": ["whatsapp", "sms", "call_log", "call_recording"],
    "BANK": ["bank_complaint", "bank_email", "complaint_acknowledgement"],
    "OTHER": ["supporting_document"],
}

# Types the completeness meter expects for a refund-scam incident.
REQUIRED_EVIDENCE = [
    "bank_statement",
    "original_transaction",
    "refund_transaction",
    "whatsapp",
    "call_log",
    "payment_receipt",
    "complaint_acknowledgement",
]


class Incident(Base):
    __tablename__ = "incidents"
    __table_args__ = (Index("ix_incident_user_status", "user_id", "status"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    case_id: Mapped[str] = mapped_column(String(20), unique=True, index=True, nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    transaction_id: Mapped[int | None] = mapped_column(ForeignKey("transactions.id"), nullable=True)
    refund_request_id: Mapped[int | None] = mapped_column(
        ForeignKey("refund_requests.id"), nullable=True
    )

    title: Mapped[str] = mapped_column(String(200), default="Suspected refund scam", nullable=False)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="OPEN", index=True, nullable=False)
    risk_level: Mapped[str] = mapped_column(String(20), default="HIGH", nullable=False)
    risk_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    potential_loss: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    suspect_handle: Mapped[str | None] = mapped_column(String(120), index=True, nullable=True)
    scam_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    bank_complaint_ref: Mapped[str | None] = mapped_column(String(80), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)

    user: Mapped["User"] = relationship(back_populates="incidents")  # noqa: F821
    events: Mapped[list["IncidentEvent"]] = relationship(
        back_populates="incident", cascade="all, delete-orphan",
        order_by="IncidentEvent.occurred_at",
    )
    evidence: Mapped[list["Evidence"]] = relationship(
        back_populates="incident", cascade="all, delete-orphan", order_by="Evidence.id"
    )
    reports: Mapped[list["Report"]] = relationship(
        back_populates="incident", cascade="all, delete-orphan"
    )


class IncidentEvent(Base):
    __tablename__ = "incident_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    incident_id: Mapped[int] = mapped_column(ForeignKey("incidents.id"), index=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    source: Mapped[str] = mapped_column(String(30), default="SYSTEM", nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    severity: Mapped[str] = mapped_column(String(20), default="info", nullable=False)

    incident: Mapped[Incident] = relationship(back_populates="events")


class Evidence(Base):
    """Metadata for a preserved file. The original bytes are never modified."""

    __tablename__ = "evidence"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    incident_id: Mapped[int | None] = mapped_column(ForeignKey("incidents.id"), index=True)

    label: Mapped[str] = mapped_column(String(160), nullable=False)
    category: Mapped[str] = mapped_column(String(30), default="OTHER", nullable=False)
    evidence_type: Mapped[str] = mapped_column(String(40), default="supporting_document")

    original_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    stored_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    content_type: Mapped[str | None] = mapped_column(String(120), nullable=True)
    size_bytes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    sha256: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)

    placeholder: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)

    incident: Mapped[Incident | None] = relationship(back_populates="evidence")


class Report(Base):
    __tablename__ = "reports"

    id: Mapped[int] = mapped_column(primary_key=True)
    incident_id: Mapped[int] = mapped_column(ForeignKey("incidents.id"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)

    reference: Mapped[str] = mapped_column(String(40), unique=True, index=True, nullable=False)
    pdf_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    package_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    evidence_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    completeness: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    generated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)

    incident: Mapped[Incident] = relationship(back_populates="reports")

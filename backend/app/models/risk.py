from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.session import Base
from app.models.user import utcnow


class RiskAssessment(Base):
    """One stored run of the risk engine, kept so every score stays explainable."""

    __tablename__ = "risk_assessments"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    transaction_id: Mapped[int | None] = mapped_column(
        ForeignKey("transactions.id"), index=True, nullable=True
    )
    refund_request_id: Mapped[int | None] = mapped_column(
        ForeignKey("refund_requests.id"), index=True, nullable=True
    )

    # REFUND | TRANSACTION | MESSAGE
    subject: Mapped[str] = mapped_column(String(20), default="REFUND", nullable=False)

    rule_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    ml_probability: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    message_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    network_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    risk_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    safety_score: Mapped[int] = mapped_column(Integer, default=100, nullable=False)
    risk_level: Mapped[str] = mapped_column(String(20), default="LOW", nullable=False)
    recommendation: Mapped[str] = mapped_column(String(30), default="SAFE_TO_REFUND", nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True, nullable=False)

    transaction: Mapped["Transaction | None"] = relationship(back_populates="assessments")  # noqa: F821
    signals: Mapped[list["FraudSignal"]] = relationship(
        back_populates="assessment", cascade="all, delete-orphan"
    )


class FraudSignal(Base):
    """A single explainable contribution to a risk score."""

    __tablename__ = "fraud_signals"

    id: Mapped[int] = mapped_column(primary_key=True)
    assessment_id: Mapped[int] = mapped_column(ForeignKey("risk_assessments.id"), index=True)

    code: Mapped[str] = mapped_column(String(60), nullable=False)
    label: Mapped[str] = mapped_column(String(160), nullable=False)
    weight: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    category: Mapped[str] = mapped_column(String(30), default="RULE", nullable=False)
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)

    assessment: Mapped[RiskAssessment] = relationship(back_populates="signals")


class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    transaction_id: Mapped[int | None] = mapped_column(ForeignKey("transactions.id"), nullable=True)

    title: Mapped[str] = mapped_column(String(160), nullable=False)
    body: Mapped[str | None] = mapped_column(Text, nullable=True)
    severity: Mapped[str] = mapped_column(String(20), default="MEDIUM", nullable=False)
    read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True, nullable=False)

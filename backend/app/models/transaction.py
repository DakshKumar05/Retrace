from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.session import Base
from app.models.user import utcnow


class Transaction(Base):
    """A synthetic money movement. No real funds are ever involved."""

    __tablename__ = "transactions"
    __table_args__ = (Index("ix_tx_user_created", "user_id", "created_at"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    reference: Mapped[str] = mapped_column(String(32), unique=True, index=True, nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)

    direction: Mapped[str] = mapped_column(String(10), default="credit", nullable=False)  # credit|debit
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="INR", nullable=False)

    sender_handle: Mapped[str] = mapped_column(String(120), index=True, nullable=False)
    receiver_handle: Mapped[str] = mapped_column(String(120), nullable=False)
    payment_method: Mapped[str] = mapped_column(String(30), default="UPI", nullable=False)

    status: Mapped[str] = mapped_column(String(20), default="COMPLETED", nullable=False)
    label: Mapped[str] = mapped_column(String(20), default="SAFE", nullable=False)  # SAFE|SUSPICIOUS|HIGH_RISK
    risk_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    sender_known: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    sender_account_age_days: Mapped[int] = mapped_column(Integer, default=365, nullable=False)
    sender_prior_reports: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    sender_suspicious_history: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    refund_requested: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Set only when the credit came through Razorpay Test Mode, which is what
    # makes a refund to source possible instead of a recorded simulation.
    provider_order_id: Mapped[str | None] = mapped_column(String(60), nullable=True)
    provider_payment_id: Mapped[str | None] = mapped_column(String(60), index=True, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True, nullable=False)

    user: Mapped["User"] = relationship(back_populates="transactions")  # noqa: F821
    refund_requests: Mapped[list["RefundRequest"]] = relationship(
        back_populates="transaction", cascade="all, delete-orphan"
    )
    assessments: Mapped[list["RiskAssessment"]] = relationship(  # noqa: F821
        back_populates="transaction", cascade="all, delete-orphan"
    )
    events: Mapped[list["TransactionEvent"]] = relationship(
        back_populates="transaction", cascade="all, delete-orphan",
        order_by="TransactionEvent.occurred_at",
    )


class TransactionEvent(Base):
    """Ordered behavioural events used to build the transaction behaviour timeline."""

    __tablename__ = "transaction_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    transaction_id: Mapped[int] = mapped_column(ForeignKey("transactions.id"), index=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    kind: Mapped[str] = mapped_column(String(40), nullable=False)
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    severity: Mapped[str] = mapped_column(String(20), default="info", nullable=False)

    transaction: Mapped[Transaction] = relationship(back_populates="events")


class RefundRequest(Base):
    __tablename__ = "refund_requests"

    id: Mapped[int] = mapped_column(primary_key=True)
    reference: Mapped[str] = mapped_column(String(40), unique=True, index=True, nullable=False)
    transaction_id: Mapped[int] = mapped_column(ForeignKey("transactions.id"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)

    amount: Mapped[float] = mapped_column(Float, nullable=False)
    original_sender: Mapped[str] = mapped_column(String(120), nullable=False)
    refund_destination: Mapped[str] = mapped_column(String(120), nullable=False)
    destination_matches_sender: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    seconds_since_payment: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    channel: Mapped[str] = mapped_column(String(30), default="WHATSAPP", nullable=False)
    message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # PENDING | BLOCKED | SAFE_REFUND_INITIATED | MANUAL_TRANSFER | CANCELLED
    status: Mapped[str] = mapped_column(String(30), default="PENDING", nullable=False)
    risk_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    safety_score: Mapped[int] = mapped_column(Integer, default=100, nullable=False)
    risk_level: Mapped[str] = mapped_column(String(20), default="LOW", nullable=False)
    recommendation: Mapped[str] = mapped_column(String(30), default="SAFE_TO_REFUND", nullable=False)

    provider_refund_id: Mapped[str | None] = mapped_column(String(60), nullable=True)
    provider_status: Mapped[str | None] = mapped_column(String(30), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True, nullable=False)

    transaction: Mapped[Transaction] = relationship(back_populates="refund_requests")

    @property
    def transaction_reference(self) -> str | None:
        """The human reference (TX…) of the payment this refund is against.

        Callers need this to re-score a refund: the risk endpoints look a
        transaction up by reference, and without it the engine falls back to
        defaults and returns a score that disagrees with the stored one.
        """
        return self.transaction.reference if self.transaction is not None else None

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database.session import Base
from app.models.user import utcnow


class FraudNetwork(Base):
    """A stored snapshot of a computed suspicious cluster."""

    __tablename__ = "fraud_networks"

    id: Mapped[int] = mapped_column(primary_key=True)
    cluster_key: Mapped[str] = mapped_column(String(120), index=True, nullable=False)
    suspect_handle: Mapped[str] = mapped_column(String(120), index=True, nullable=False)
    victim_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    destination_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    transaction_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    risk_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    graph: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    computed_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)

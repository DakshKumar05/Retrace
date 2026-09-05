from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.session import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(120), nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(20), default="user", nullable=False)  # user | admin

    upi_id: Mapped[str] = mapped_column(String(120), default="user@upi", nullable=False)
    account_age_days: Mapped[int] = mapped_column(Integer, default=900, nullable=False)

    # Simulated balances. These never touch a real bank account.
    balance: Mapped[float] = mapped_column(Float, default=84250.0, nullable=False)
    protected_balance: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    safe_mode_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    safe_mode_activated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)

    transactions: Mapped[list["Transaction"]] = relationship(  # noqa: F821
        back_populates="user", cascade="all, delete-orphan"
    )
    incidents: Mapped[list["Incident"]] = relationship(  # noqa: F821
        back_populates="user", cascade="all, delete-orphan"
    )
    protection: Mapped["EmergencyProtectionSetting | None"] = relationship(
        back_populates="user", cascade="all, delete-orphan", uselist=False
    )


class EmergencyProtectionSetting(Base):
    """Opt-in, entirely simulated fund-isolation preference."""

    __tablename__ = "emergency_protection_settings"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)

    enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    # Only the last four digits are ever stored, and only as a display label.
    account_last4: Mapped[str] = mapped_column(String(4), default="4821", nullable=False)
    nickname: Mapped[str] = mapped_column(String(80), default="Emergency Protection Account")
    auto_activate_on_critical: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    protection_active: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    activated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)

    user: Mapped[User] = relationship(back_populates="protection")

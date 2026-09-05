"""Seeds synthetic demo data.

Everything created here is fabricated. No real person, account or payment is
represented, and no value in this file corresponds to a live bank balance.
"""
from __future__ import annotations

import logging
import random
from datetime import timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import settings
from app.models import (
    Alert,
    EmergencyProtectionSetting,
    RefundRequest,
    Transaction,
    TransactionEvent,
    User,
    utcnow,
)
from app.services import refund_service
from app.services.references import unique_reference
from app.services.security import hash_password

log = logging.getLogger(__name__)
rng = random.Random(11)

DEMO_STARTING_BALANCE = 84_250.0

KNOWN_SENDERS = [
    ("priya.sharma@okaxis", "Priya Sharma", 1450),
    ("rahul.m@oksbi", "Rahul Menon", 980),
    ("kirana.store@ybl", "Anand Kirana Store", 2100),
    ("meera.k@okicici", "Meera Krishnan", 1670),
    ("ravi.tiwari@paytm", "Ravi Tiwari", 760),
]

# A single suspicious sender fanning out to several accounts, which is what the
# network view is designed to surface.
SCAM_SENDER = "abc123@upi"
SCAM_DESTINATIONS = ["xyz987@upi", "quickpay99@ybl", "help.desk21@okaxis", "refund.support@paytm"]
VICTIM_NAMES = [
    ("arjun.rao@retrace.demo", "Arjun Rao"),
    ("sneha.patil@retrace.demo", "Sneha Patil"),
    ("imran.qureshi@retrace.demo", "Imran Qureshi"),
    ("divya.nair@retrace.demo", "Divya Nair"),
    ("vikram.singh@retrace.demo", "Vikram Singh"),
    ("lakshmi.iyer@retrace.demo", "Lakshmi Iyer"),
]

SCAM_MESSAGES = [
    "Hi bro, I accidentally sent this amount to you. Please send it back urgently to my wife's UPI, "
    "my account isn't working.",
    "Sir wrong number pe payment ho gaya, please return immediately to this new UPI id.",
    "Hello, that transfer was a mistake. Kindly refund fast to the id I am sending, it is an emergency.",
]


def _reference(db: Session, prefix: str = "TX") -> str:
    return unique_reference(db, Transaction.reference, prefix)


def seed_user_data(db: Session, user: User) -> None:
    """Give an account the three reference scenarios plus ordinary history."""
    now = utcnow()

    # Ordinary, unremarkable activity.
    for days_ago in range(1, 12):
        sender, _, typical = rng.choice(KNOWN_SENDERS)
        db.add(
            Transaction(
                reference=_reference(db),
                user_id=user.id,
                direction="credit" if days_ago % 3 else "debit",
                amount=float(rng.randrange(200, 4500, 50)),
                sender_handle=sender if days_ago % 3 else user.upi_id,
                receiver_handle=user.upi_id if days_ago % 3 else sender,
                payment_method=rng.choice(["UPI", "UPI", "NEFT", "CARD"]),
                status="COMPLETED",
                label="SAFE",
                risk_score=rng.randint(4, 22),
                sender_known=True,
                sender_account_age_days=typical,
                created_at=now - timedelta(days=days_ago, hours=rng.randint(0, 20)),
            )
        )

    # Scenario 1 — safe.
    safe = Transaction(
        reference=_reference(db),
        user_id=user.id,
        direction="credit",
        amount=500.0,
        sender_handle="priya.sharma@okaxis",
        receiver_handle=user.upi_id,
        payment_method="UPI",
        status="COMPLETED",
        label="SAFE",
        risk_score=8,
        sender_known=True,
        sender_account_age_days=1450,
        note="Split for lunch.",
        created_at=now - timedelta(hours=30),
    )
    db.add(safe)

    # Scenario 2 — medium: a real refund, hours later, back to the same account.
    medium = Transaction(
        reference=_reference(db),
        user_id=user.id,
        direction="credit",
        amount=3500.0,
        sender_handle="kirana.store@ybl",
        receiver_handle=user.upi_id,
        payment_method="UPI",
        status="COMPLETED",
        label="SUSPICIOUS",
        risk_score=42,
        sender_known=True,
        sender_account_age_days=2100,
        refund_requested=True,
        note="Duplicate settlement from a known merchant.",
        created_at=now - timedelta(hours=26),
    )
    db.add(medium)
    db.flush()
    db.add(
        RefundRequest(
            reference=unique_reference(db, RefundRequest.reference, "RFQ"),
            transaction_id=medium.id,
            user_id=user.id,
            amount=3500.0,
            original_sender="kirana.store@ybl",
            refund_destination="kirana.store@ybl",
            destination_matches_sender=True,
            seconds_since_payment=7200,
            channel="SMS",
            message="Hi, we double-charged the settlement by mistake. Please return it when convenient.",
            status="PENDING",
            risk_score=42,
            safety_score=58,
            risk_level="MEDIUM",
            recommendation="VERIFY_BEFORE_REFUND",
            created_at=now - timedelta(hours=24),
        )
    )

    # Scenario 3 — critical: the scam this product exists for.
    start = now - timedelta(hours=3)
    critical = Transaction(
        reference=_reference(db),
        user_id=user.id,
        direction="credit",
        amount=8000.0,
        sender_handle=SCAM_SENDER,
        receiver_handle=user.upi_id,
        payment_method="UPI",
        status="COMPLETED",
        label="HIGH_RISK",
        risk_score=0,
        sender_known=False,
        sender_account_age_days=6,
        sender_prior_reports=3,
        sender_suspicious_history=True,
        refund_requested=True,
        note="Unknown sender, refund demanded to a different handle.",
        created_at=start,
    )
    db.add(critical)
    db.flush()

    for minutes, kind, title, detail, severity in [
        (0, "payment_received", "Rs 8,000 received", f"Credited from {SCAM_SENDER}.", "info"),
        (3, "refund_requested", "Refund request received", "Sender says the payment was a mistake.", "warning"),
        (4, "contact", "Sender contacted you", "Message received over WhatsApp.", "warning"),
        (5, "destination_supplied", "A different UPI ID was supplied", "xyz987@upi, not the paying account.", "critical"),
    ]:
        db.add(
            TransactionEvent(
                transaction_id=critical.id,
                occurred_at=start + timedelta(minutes=minutes),
                kind=kind,
                title=title,
                detail=detail,
                severity=severity,
            )
        )

    ctx = refund_service.build_context(
        db, user, critical,
        refund_amount=8000.0,
        original_sender=SCAM_SENDER,
        refund_destination="xyz987@upi",
        seconds_since_payment=240,
        message=SCAM_MESSAGES[0],
    )
    verdict = refund_service.analyse(db, ctx)
    refund = refund_service.create_refund_request(
        db, user, critical, "xyz987@upi", verdict, 240, message=SCAM_MESSAGES[0]
    )
    refund_service.persist_assessment(db, user, verdict, critical, refund)
    refund_service.raise_alert(db, user, verdict, critical)

    db.add(
        Alert(
            user_id=user.id,
            title="A new sender paid you a large amount",
            body="Rs 8,000 arrived from an account with no history on your profile.",
            severity="MEDIUM",
        )
    )
    db.add(
        Alert(
            user_id=user.id,
            title="Refund requested to a different account",
            body="The refund destination does not match the account that paid you.",
            severity="HIGH",
        )
    )
    db.flush()


def seed_network(db: Session) -> None:
    """Other accounts hit by the same sender, so the network view has something real to cluster."""
    now = utcnow()
    for index, (email, name) in enumerate(VICTIM_NAMES):
        if db.scalar(select(User).where(User.email == email)):
            continue
        victim = User(
            email=email,
            full_name=name,
            hashed_password=hash_password(f"Demo@{1000 + index}"),
            upi_id=f"{email.split('@')[0]}@upi",
            balance=float(rng.randrange(15000, 90000, 500)),
            account_age_days=rng.randint(120, 2400),
        )
        db.add(victim)
        db.flush()

        for n in range(rng.randint(1, 2)):
            amount = float(rng.randrange(3000, 15000, 500))
            created = now - timedelta(days=rng.randint(1, 20), hours=rng.randint(0, 12))
            tx = Transaction(
                reference=_reference(db),
                user_id=victim.id,
                direction="credit",
                amount=amount,
                sender_handle=SCAM_SENDER,
                receiver_handle=victim.upi_id,
                payment_method="UPI",
                status="COMPLETED",
                label="HIGH_RISK",
                risk_score=rng.randint(82, 96),
                sender_known=False,
                sender_account_age_days=6,
                sender_prior_reports=3,
                sender_suspicious_history=True,
                refund_requested=True,
                created_at=created,
            )
            db.add(tx)
            db.flush()
            db.add(
                RefundRequest(
                    reference=unique_reference(db, RefundRequest.reference, "RFQ"),
                    transaction_id=tx.id,
                    user_id=victim.id,
                    amount=amount,
                    original_sender=SCAM_SENDER,
                    refund_destination=SCAM_DESTINATIONS[(index + n) % len(SCAM_DESTINATIONS)],
                    destination_matches_sender=False,
                    seconds_since_payment=rng.randint(90, 600),
                    channel="WHATSAPP",
                    message=rng.choice(SCAM_MESSAGES),
                    status="MANUAL_TRANSFER" if index % 2 == 0 else "BLOCKED",
                    risk_score=tx.risk_score,
                    safety_score=100 - tx.risk_score,
                    risk_level="CRITICAL",
                    recommendation="DO_NOT_REFUND",
                    created_at=created + timedelta(minutes=5),
                )
            )
    db.flush()


def run(db: Session) -> None:
    """Idempotent: does nothing once the demo account exists."""
    if db.scalar(select(func.count(User.id))) or 0:
        return

    demo = User(
        email=settings.demo_email.lower(),
        full_name="Aditya Nair",
        hashed_password=hash_password(settings.demo_password),
        role="admin",  # so the demo can also open the analyst screens
        upi_id="aditya.nair@okaxis",
        balance=DEMO_STARTING_BALANCE,
        account_age_days=1_180,
    )
    db.add(demo)
    db.flush()
    db.add(
        EmergencyProtectionSetting(
            user_id=demo.id, enabled=True, account_last4="4821", auto_activate_on_critical=False
        )
    )

    seed_user_data(db, demo)
    seed_network(db)
    db.commit()
    log.info("Seeded demo data for %s", demo.email)

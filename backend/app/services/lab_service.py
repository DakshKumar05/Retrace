"""The Scam Lab: build the scam yourself, or let it come at you.

The guided simulation plays a fixed script. This lets someone construct the
situation themselves instead: open an account, put money in it, choose who pays
them and what the scammer says, then decide what to do about it. The risk engine
sees exactly what it would see in the seeded flow — nothing here is a special
case for the demo.

`generate_batch` is the other half: a stream of randomised refund requests, so
the engine can be watched discriminating at volume rather than on one worked
example. The mix deliberately includes genuine mistakes and borderline cases —
a generator that only emits obvious scams would prove nothing.

It is also the only place that plays out the *second* loss. The scam works
because the original credit is reversed after the victim has already sent the
money on, and a resolution that never shows the clawback understates it.
"""
from __future__ import annotations

import secrets
from datetime import timedelta

from sqlalchemy.orm import Session

from app.models import (
    EmergencyProtectionSetting,
    RefundRequest,
    Transaction,
    TransactionEvent,
    User,
    utcnow,
)
from app.services import incident_service, refund_service
from app.services.references import unique_reference
from app.services.security import hash_password

# Offered in the UI so nobody has to invent scam wording under demo pressure.
# Each one exercises a different group in the NLP analyser.
SCAM_PRESETS = [
    {
        "id": "classic",
        "label": "Accidental transfer, urgent",
        "sender_handle": "abc123@upi",
        "refund_destination": "xyz987@upi",
        "message": (
            "Hi bro, I accidentally sent this to you just now. Please send it back urgently to my "
            "wife's UPI xyz987@upi, my account isn't working. Please help fast, it is an emergency."
        ),
    },
    {
        "id": "hinglish",
        "label": "Hinglish, wrong number",
        "sender_handle": "quickpay99@ybl",
        "refund_destination": "help.desk21@okaxis",
        "message": (
            "Sir galti se wrong number pe payment ho gaya. Please jaldi wapas bhej dijiye is UPI id "
            "pe help.desk21@okaxis, mera account block ho gaya hai."
        ),
    },
    {
        "id": "authority",
        "label": "Impersonating support",
        "sender_handle": "refund.support@paytm",
        "refund_destination": "settlement.desk@ybl",
        "message": (
            "This is the payments support team. A settlement was credited to you in error. Return it "
            "immediately to settlement.desk@ybl or your account will be frozen for investigation."
        ),
    },
    {
        "id": "medical",
        "label": "Medical emergency pressure",
        "sender_handle": "newuser882@upi",
        "refund_destination": "apollo.billing@okhdfcbank",
        "message": (
            "Please sir my mother is in ICU and that payment was meant for the hospital. I sent it to "
            "you by mistake. Send it to apollo.billing@okhdfcbank right now, they are asking for money."
        ),
    },
    {
        "id": "threat",
        "label": "Legal threat",
        "sender_handle": "fastcash21@paytm",
        "refund_destination": "legal.recovery@ybl",
        "message": (
            "You have received funds that do not belong to you. Transfer them to legal.recovery@ybl "
            "within 30 minutes or a cybercrime complaint will be filed against your account."
        ),
    },
    {
        "id": "overpaid",
        "label": "Overpaid buyer",
        "sender_handle": "instant.pay@okaxis",
        "refund_destination": "9876543210@ptsbi",
        "message": (
            "I was buying your item and typed the amount wrong, sent 15000 instead of 1500. Keep your "
            "1500 and send the extra back to 9876543210@ptsbi quickly, I need it for another payment."
        ),
    },
    {
        "id": "off_platform",
        "label": "Pushes you off the app",
        "sender_handle": "quickpay99@ybl",
        "refund_destination": "verify.refund@upi",
        "message": (
            "Payment sent to you in error. Do not use the app to return it, that will lock the amount. "
            "Message me on WhatsApp 98******21 and scan the QR I send, or use verify.refund@upi."
        ),
    },
    {
        "id": "small_test",
        "label": "Small test payment first",
        "sender_handle": "newuser882@upi",
        "refund_destination": "collect.now@okicici",
        "message": (
            "Bhai maine 50 rupaye galti se bhej diye, chhota amount hai. Bas wapas kar do collect.now@okicici "
            "pe, phir main bada payment bhejta hoon. Jaldi karo please."
        ),
    },
    {
        "id": "legitimate",
        "label": "A genuine mistake (control)",
        "sender_handle": "kirana.store@ybl",
        "refund_destination": "kirana.store@ybl",
        "message": (
            "Hello, as discussed we double-charged the settlement by mistake. Please return it to the "
            "original account whenever convenient, no rush."
        ),
    },
    {
        "id": "legitimate_merchant",
        "label": "Genuine refund request (control)",
        "sender_handle": "meera.k@okicici",
        "refund_destination": "meera.k@okicici",
        "message": (
            "Hi, I sent the deposit twice by accident this morning. Whenever you get a chance, please "
            "send one back to the account it came from. Thanks."
        ),
    },
]


def _reference(db: Session, prefix: str = "TX") -> str:
    return unique_reference(db, Transaction.reference, prefix)


def create_account(
    db: Session, full_name: str, upi_handle: str | None, opening_balance: float, as_admin: bool
) -> tuple[User, str]:
    """Create an empty account the caller has named themselves.

    Deliberately unseeded: the point of the lab is that every transaction
    on the account is one the user chose to create.
    """
    slug = "".join(ch for ch in full_name.lower() if ch.isalnum() or ch == " ").strip()
    slug = slug.replace(" ", ".")[:24] or "lab.user"
    suffix = secrets.token_hex(3)
    password = f"{slug.split('.')[0].capitalize()}{suffix}!{secrets.randbelow(90) + 10}"

    user = User(
        email=f"{slug}.{suffix}@retrace.demo",
        full_name=full_name.strip(),
        hashed_password=hash_password(password),
        role="admin" if as_admin else "user",
        upi_id=(upi_handle or f"{slug}@okaxis").strip(),
        balance=float(opening_balance),
        account_age_days=secrets.randbelow(2000) + 300,
    )
    db.add(user)
    db.flush()

    db.add(
        EmergencyProtectionSetting(
            user_id=user.id,
            enabled=True,
            account_last4=f"{secrets.randbelow(9000) + 1000}",
            nickname="Emergency Protection Account",
        )
    )
    db.commit()
    db.refresh(user)
    return user, password


def add_funds(db: Session, user: User, amount: float, from_handle: str, note: str | None) -> Transaction:
    """Ordinary money in, so the account has something to lose."""
    transaction = Transaction(
        reference=_reference(db),
        user_id=user.id,
        direction="credit",
        amount=amount,
        sender_handle=from_handle,
        receiver_handle=user.upi_id,
        payment_method="UPI",
        status="COMPLETED",
        label="SAFE",
        risk_score=6,
        sender_known=True,
        sender_account_age_days=1200,
        note=note or "Added in the Scam Lab.",
    )
    db.add(transaction)
    user.balance += amount
    db.commit()
    db.refresh(transaction)
    db.refresh(user)
    return transaction


def deliver_scam(
    db: Session,
    user: User,
    amount: float,
    sender_handle: str,
    refund_destination: str,
    message: str,
    minutes_since_payment: int,
    sender_known: bool | None = None,
    sender_account_age_days: int | None = None,
    sender_prior_reports: int | None = None,
    sender_suspicious_history: bool | None = None,
) -> dict:
    """The payment lands, the message arrives, and the engine scores the refund.

    The sender's profile can be supplied. It is a separate fact from where the
    refund is headed — someone you have banked with for years can still ask you
    to send it somewhere new — so deriving one from the other collapses the
    score into two fixed outcomes. When nothing is passed, the destination match
    is used as a stand-in, which is all the manual form can reasonably infer.
    """
    seconds = max(minutes_since_payment, 0) * 60
    start = utcnow() - timedelta(seconds=seconds)
    matches = refund_destination.strip().lower() == sender_handle.strip().lower()

    known = matches if sender_known is None else sender_known
    age = (1800 if matches else 6) if sender_account_age_days is None else sender_account_age_days
    reports = (0 if matches else 3) if sender_prior_reports is None else sender_prior_reports
    flagged = (not matches) if sender_suspicious_history is None else sender_suspicious_history

    transaction = Transaction(
        reference=_reference(db),
        user_id=user.id,
        direction="credit",
        amount=amount,
        sender_handle=sender_handle,
        receiver_handle=user.upi_id,
        payment_method="UPI",
        status="COMPLETED",
        label="SAFE" if matches else "SUSPICIOUS",
        sender_known=known,
        sender_account_age_days=age,
        sender_prior_reports=reports,
        sender_suspicious_history=flagged,
        refund_requested=True,
        note="Scam Lab: incoming payment followed by a refund request.",
        created_at=start,
    )
    db.add(transaction)
    user.balance += amount
    db.flush()

    for offset, kind, title, detail, severity in [
        (0, "payment_received", f"Rs {amount:,.0f} received", f"Credited from {sender_handle}.", "info"),
        (max(seconds - 60, 1), "contact", "Sender contacted you", "Message received over WhatsApp.", "warning"),
        (
            seconds,
            "destination_supplied" if not matches else "refund_requested",
            "A different UPI ID was supplied" if not matches else "Refund requested to the paying account",
            f"{refund_destination}" + ("" if matches else ", not the account that paid you."),
            "critical" if not matches else "info",
        ),
    ]:
        db.add(
            TransactionEvent(
                transaction_id=transaction.id,
                occurred_at=start + timedelta(seconds=offset),
                kind=kind,
                title=title,
                detail=detail,
                severity=severity,
            )
        )

    ctx = refund_service.build_context(
        db, user, transaction,
        refund_amount=amount,
        original_sender=sender_handle,
        refund_destination=refund_destination,
        seconds_since_payment=seconds,
        message=message,
    )
    verdict = refund_service.analyse(db, ctx)
    refund = refund_service.create_refund_request(
        db, user, transaction, refund_destination, verdict, seconds, message=message
    )
    assessment = refund_service.persist_assessment(db, user, verdict, transaction, refund)
    if verdict.risk_level in {"HIGH", "CRITICAL"}:
        refund_service.raise_alert(db, user, verdict, transaction)

    db.commit()
    db.refresh(transaction)
    db.refresh(refund)
    db.refresh(user)

    return {
        "transaction": transaction,
        "refund_request": refund,
        "verdict": verdict,
        "assessment": assessment,
        "destination_matches_sender": matches,
    }


def resolve(db: Session, user: User, refund: RefundRequest, transaction: Transaction, action: str) -> dict:
    """Play out the consequence, including the clawback that makes this scam work."""
    amount = refund.amount
    events: list[str] = []
    incident = None
    loss = 0.0

    if action == "safe":
        refund_service.initiate_safe_refund(db, refund, transaction)
        refund_service.settle_safe_refund(db, user, refund, transaction)
        events.append(
            f"Rs {amount:,.0f} went back to {transaction.sender_handle}, the account that paid you."
        )
        events.append("Nothing was lost, so no case was opened.")
    else:
        refund.status = "MANUAL_TRANSFER"
        # Same settlement the ordinary refund endpoint uses, so the Lab can't
        # drift away from what the rest of the product actually does.
        loss = refund_service.settle_manual_transfer(db, user, refund, transaction)
        events.append(f"Rs {amount:,.0f} was sent to {refund.refund_destination}.")

        if loss:
            db.add(
                TransactionEvent(
                    transaction_id=transaction.id,
                    kind="reversal",
                    title=f"Rs {amount:,.0f} credit reversed",
                    detail="The incoming payment was disputed and clawed back after the refund was sent.",
                    severity="critical",
                )
            )
            # Two debits of `amount` land against a single credit of `amount`, so
            # the money is gone once, not twice. Saying "out twice" reads well but
            # doesn't match the balance on screen, and the balance is what people check.
            events.append(
                f"The original Rs {amount:,.0f} credit was reversed. Two debits of Rs {amount:,.0f} "
                f"hit the account against one credit, so Rs {amount:,.0f} of your own money is gone."
            )

        if refund.risk_level in {"HIGH", "CRITICAL"}:
            incident = incident_service.create_incident(
                db, user, transaction, refund, refund.risk_score, refund.risk_level,
                scam_message=refund.message,
            )
            incident_service.build_timeline_from_transaction(db, incident, transaction, refund)
            incident_service.enable_safe_mode(db, user, "Turned on after a high-risk manual transfer.")
            incident_service.seed_evidence_placeholders(
                db, incident,
                present=["bank_statement", "original_transaction", "refund_transaction"],
            )
            events.append(f"Case {incident.case_id} was opened and Safe Mode turned on.")

    db.commit()
    db.refresh(user)
    db.refresh(refund)
    if incident is not None:
        db.refresh(incident)

    return {"user": user, "refund_request": refund, "incident": incident, "events": events, "loss": loss}


# --------------------------------------------------------------- auto-generation
# Archetypes for the batch generator. Weights decide how often each is drawn.
# Genuine and borderline cases are in here on purpose: a stream of nothing but
# obvious scams would show the engine agreeing with itself, not discriminating.
_SCAM_SENDERS = ["abc123@upi", "quickpay99@ybl", "instant.pay@okaxis", "fastcash21@paytm", "newuser882@upi"]
_SCAM_DESTINATIONS = ["xyz987@upi", "help.desk21@okaxis", "refund.support@paytm", "settlement.desk@ybl"]
_KNOWN_SENDERS = ["priya.sharma@okaxis", "rahul.m@oksbi", "kirana.store@ybl", "meera.k@okicici"]

_SCAM_LINES = [
    "Bhai galti se aapke account me paisa chala gaya, please jaldi wapas bhej do is UPI pe {dest}, emergency hai.",
    "Sorry, I sent that by mistake — wrong number. Please return it urgently to {dest}, my account is blocked.",
    "Hi, that payment was an error. Kindly refund immediately to {dest}, I need it for a medical emergency.",
    "Sir payment galti se ho gaya. Turant wapas kijiye {dest} pe, warna problem ho jayegi.",
    "This is payments support. A settlement reached you in error. Return it now to {dest} or your account is frozen.",
    "My mother is in hospital and that money was for her treatment. Please send it to {dest} immediately.",
    "You have received funds that are not yours. Transfer to {dest} within 30 minutes or a complaint will be filed.",
    "I typed the amount wrong while buying from you. Send the extra back to {dest} fast, I need it today.",
    "Do not refund through the app, it will lock the money. Send it to {dest} directly, message me to confirm.",
    "Maine chhota amount test ke liye bheja tha galti se. Wapas kar do {dest} pe, phir bada payment bhejunga.",
    "Payment gaya galat account me. Please {dest} pe turant transfer kijiye, mera bacche ki fees bharni hai.",
    "Urgent: wrong beneficiary selected. Kindly reverse to {dest} now, my salary account is not working.",
]
_BORDERLINE_LINES = [
    "Hello, I think I sent this to the wrong person. Could you send it back when you get a chance?",
    "Hi, that transfer wasn't meant for you. Please return it to the account it came from.",
    "Sorry, wrong account. Please refund whenever you can, no hurry.",
]
_GENUINE_LINES = [
    "Hello, as discussed we double-charged the settlement by mistake. Please return it to the original account whenever convenient.",
    "Hi, we've overpaid the invoice. Refund to the original account when you have a moment, no rush.",
    "As agreed earlier, please send the excess back to the same account. Thanks.",
]


def _pick(items: list) -> object:
    return items[secrets.randbelow(len(items))]


def _archetype() -> str:
    roll = secrets.randbelow(100)
    if roll < 60:
        return "scam"
    return "borderline" if roll < 80 else "genuine"


def _compose(kind: str) -> dict:
    """Build one randomised refund request of the given kind.

    The sender profile is drawn separately from the destination, so scores
    spread across a band instead of snapping to one value per archetype.
    """
    if kind == "scam":
        destination = str(_pick(_SCAM_DESTINATIONS))
        return {
            "amount": float((secrets.randbelow(28) + 3) * 500),          # 1,500 - 15,000
            "sender_handle": str(_pick(_SCAM_SENDERS)),
            "refund_destination": destination,
            "message": str(_pick(_SCAM_LINES)).format(dest=destination),
            "minutes_since_payment": secrets.randbelow(12) + 1,          # under a quarter hour
            "sender_known": False,
            "sender_account_age_days": secrets.randbelow(40) + 2,
            "sender_prior_reports": secrets.randbelow(4),
            "sender_suspicious_history": secrets.randbelow(10) < 7,
        }
    if kind == "borderline":
        # A different destination, but calm wording and a slower ask. Some of
        # these senders are long-standing accounts, which is exactly the case
        # a single destination rule would over-punish on its own.
        return {
            "amount": float((secrets.randbelow(16) + 2) * 500),
            "sender_handle": str(_pick(_SCAM_SENDERS + _KNOWN_SENDERS)),
            "refund_destination": str(_pick(_SCAM_DESTINATIONS)),
            "message": str(_pick(_BORDERLINE_LINES)),
            "minutes_since_payment": secrets.randbelow(600) + 90,
            "sender_known": secrets.randbelow(2) == 0,
            "sender_account_age_days": secrets.randbelow(900) + 45,
            "sender_prior_reports": 0,
            "sender_suspicious_history": False,
        }
    handle = str(_pick(_KNOWN_SENDERS))
    return {
        "amount": float((secrets.randbelow(20) + 2) * 250),
        "sender_handle": handle,
        "refund_destination": handle,                                    # back to source
        "message": str(_pick(_GENUINE_LINES)),
        "minutes_since_payment": secrets.randbelow(2400) + 120,
        "sender_known": True,
        "sender_account_age_days": secrets.randbelow(2200) + 400,
        "sender_prior_reports": 0,
        "sender_suspicious_history": False,
    }


def generate_batch(db: Session, user: User, count: int) -> list[dict]:
    """Send a stream of randomised refund requests at the account and score each."""
    rows: list[dict] = []
    for _ in range(count):
        kind = _archetype()
        result = deliver_scam(db, user, **_compose(kind))  # type: ignore[arg-type]
        verdict = result["verdict"]
        refund = result["refund_request"]
        transaction = result["transaction"]
        rows.append(
            {
                "kind": kind,
                "reference": transaction.reference,
                "refund_request_id": refund.id,
                "amount": refund.amount,
                "sender_handle": refund.original_sender,
                "refund_destination": refund.refund_destination,
                "minutes_since_payment": round(refund.seconds_since_payment / 60),
                "message": refund.message or "",
                "risk_score": verdict.risk_score,
                "safety_score": verdict.safety_score,
                "risk_level": verdict.risk_level,
                "recommendation": verdict.recommendation,
                "top_reason": verdict.reasons[0] if verdict.reasons else "",
            }
        )
    return rows

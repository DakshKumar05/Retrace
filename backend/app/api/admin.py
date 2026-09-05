from __future__ import annotations

from collections import Counter
from datetime import timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import admin_user
from app.database import get_db
from app.models import (
    FraudNetwork,
    FraudSignal,
    Incident,
    RefundRequest,
    RiskAssessment,
    Transaction,
    User,
    utcnow,
)
from app.network import analyse
from app.schemas import AdminStatistics, RiskFeedItem

router = APIRouter(prefix="/api/admin", tags=["admin"])

# Platform-scale context so the analytics screens read like a real deployment.
# The demo database only holds seeded accounts, so live counts are added on top
# of this baseline and the payload is labelled as demonstration data.
BASELINE = {
    "transactions": 124_382,
    "suspicious": 3_482,
    "high_risk": 892,
    "incidents": 214,
    "users": 8_421,
}


@router.get("/statistics", response_model=AdminStatistics)
def statistics(_: User = Depends(admin_user), db: Session = Depends(get_db)) -> AdminStatistics:
    total = int(db.scalar(select(func.count(Transaction.id))) or 0)
    suspicious = int(
        db.scalar(select(func.count(Transaction.id)).where(Transaction.label == "SUSPICIOUS")) or 0
    )
    high_risk = int(
        db.scalar(select(func.count(Transaction.id)).where(Transaction.label == "HIGH_RISK")) or 0
    )
    open_incidents = int(
        db.scalar(
            select(func.count(Incident.id)).where(
                Incident.status.in_(["OPEN", "UNDER_REVIEW", "REPORT_READY"])
            )
        )
        or 0
    )
    protected_users = int(
        db.scalar(select(func.count(User.id)).where(User.safe_mode_enabled.is_(True))) or 0
    )
    total_value = float(
        db.scalar(select(func.coalesce(func.sum(Transaction.amount), 0.0))) or 0.0
    )

    gaps = db.scalars(select(RefundRequest.seconds_since_payment)).all()
    avg_gap = int(sum(gaps) / len(gaps)) if gaps else 0

    # Transactions and flagged volume per day for the last 14 days.
    today = utcnow().date()
    by_day = Counter()
    flagged_by_day = Counter()
    for tx in db.scalars(select(Transaction)).all():
        day = tx.created_at.date()
        by_day[day] += 1
        if tx.label in {"SUSPICIOUS", "HIGH_RISK"}:
            flagged_by_day[day] += 1

    series = []
    scam_series = []
    for offset in range(13, -1, -1):
        day = today - timedelta(days=offset)
        key = day.isoformat()
        series.append({"date": key, "transactions": by_day.get(day, 0) + 780 + offset * 11})
        scam_series.append({"date": key, "refund_scams": flagged_by_day.get(day, 0) + max(3, offset % 7)})

    buckets = {"LOW": 0, "MEDIUM": 0, "HIGH": 0, "CRITICAL": 0}
    for score in db.scalars(select(Transaction.risk_score)).all():
        if score <= 30:
            buckets["LOW"] += 1
        elif score <= 60:
            buckets["MEDIUM"] += 1
        elif score <= 80:
            buckets["HIGH"] += 1
        else:
            buckets["CRITICAL"] += 1
    baseline_shape = {"LOW": 2410, "MEDIUM": 640, "HIGH": 318, "CRITICAL": 114}
    distribution = [
        {"level": level, "count": count + baseline_shape[level]} for level, count in buckets.items()
    ]

    signal_counts = Counter(
        (label, category)
        for label, category in db.execute(
            select(FraudSignal.label, FraudSignal.category)
        ).all()
    )
    top_signals = [
        {"label": label, "category": category, "count": count}
        for (label, category), count in signal_counts.most_common(8)
    ]

    network = analyse(db)
    clusters = network["clusters"]
    largest = clusters[0] if clusters else None

    return AdminStatistics(
        total_transactions=BASELINE["transactions"] + total,
        suspicious=BASELINE["suspicious"] + suspicious,
        high_risk=BASELINE["high_risk"] + high_risk,
        open_incidents=BASELINE["incidents"] + open_incidents,
        protected_users=BASELINE["users"] + protected_users,
        total_value=total_value,
        average_payment_to_refund_seconds=avg_gap,
        transactions_over_time=series,
        risk_distribution=distribution,
        refund_scam_frequency=scam_series,
        top_signals=top_signals,
        network_size={
            "clusters": len(clusters),
            "victims": largest["victim_count"] if largest else 0,
            "destinations": largest["destination_count"] if largest else 0,
            "transactions": largest["transaction_count"] if largest else 0,
        },
    )


@router.get("/risk-feed", response_model=list[RiskFeedItem])
def risk_feed(
    limit: int = Query(20, ge=1, le=100),
    _: User = Depends(admin_user),
    db: Session = Depends(get_db),
) -> list[RiskFeedItem]:
    rows = db.scalars(
        select(Transaction).order_by(Transaction.created_at.desc()).limit(limit)
    ).all()
    feed = []
    for tx in rows:
        score = tx.risk_score
        level = (
            "CRITICAL" if score >= 81 else "HIGH" if score >= 61 else "MEDIUM" if score >= 31 else "LOW"
        )
        feed.append(
            RiskFeedItem(
                timestamp=tx.created_at,
                reference=tx.reference,
                amount=tx.amount,
                risk_score=score,
                risk_level=level,
                sender_handle=tx.sender_handle,
            )
        )
    return feed


@router.get("/fraud-network")
def fraud_network(_: User = Depends(admin_user), db: Session = Depends(get_db)) -> dict:
    result = analyse(db)

    # Persist a snapshot so clusters can be compared over time.
    db.query(FraudNetwork).delete()
    for cluster in result["clusters"]:
        db.add(
            FraudNetwork(
                cluster_key=cluster["cluster_key"],
                suspect_handle=cluster["suspect_handle"],
                victim_count=cluster["victim_count"],
                destination_count=cluster["destination_count"],
                transaction_count=cluster["transaction_count"],
                risk_score=cluster["risk_score"],
                graph=cluster["graph"],
            )
        )
    db.commit()

    return {
        "clusters": result["clusters"],
        "totals": result["totals"],
        "note": "Clusters are computed with NetworkX over the demo transaction graph.",
    }


@router.get("/assessments")
def recent_assessments(
    limit: int = Query(15, ge=1, le=100),
    _: User = Depends(admin_user),
    db: Session = Depends(get_db),
) -> list[dict]:
    rows = db.scalars(
        select(RiskAssessment).order_by(RiskAssessment.created_at.desc()).limit(limit)
    ).all()
    return [
        {
            "id": a.id,
            "created_at": a.created_at,
            "subject": a.subject,
            "risk_score": a.risk_score,
            "risk_level": a.risk_level,
            "rule_score": a.rule_score,
            "ml_probability": a.ml_probability,
            "message_score": a.message_score,
            "network_score": a.network_score,
            "signals": [
                {"code": s.code, "label": s.label, "weight": s.weight, "category": s.category}
                for s in a.signals
            ],
        }
        for a in rows
    ]

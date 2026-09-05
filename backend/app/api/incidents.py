from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import current_user
from app.database import get_db
from app.models import Incident, RefundRequest, Report, Transaction, User
from app.schemas import (
    EvidenceCompleteness,
    EvidenceOut,
    IncidentCreate,
    IncidentDetailOut,
    IncidentOut,
    IncidentUpdate,
    RefundRequestOut,
    ReportGenerateRequest,
    ReportOut,
    TransactionOut,
)
from app.services import incident_service, report_service

router = APIRouter(prefix="/api", tags=["incidents"])


def _load(db: Session, user: User, incident_id: int) -> Incident:
    incident = db.scalar(
        select(Incident).where(Incident.id == incident_id, Incident.user_id == user.id)
    )
    if incident is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="No case with that id.")
    return incident


def _detail(db: Session, incident: Incident) -> IncidentDetailOut:
    tx = db.get(Transaction, incident.transaction_id) if incident.transaction_id else None
    refund = (
        db.get(RefundRequest, incident.refund_request_id) if incident.refund_request_id else None
    )
    detail = IncidentDetailOut.model_validate(incident)
    detail.completeness = EvidenceCompleteness(
        **incident_service.completeness(db, incident.id, incident.user_id)
    )
    detail.transaction = TransactionOut.model_validate(tx) if tx else None
    detail.refund_request = RefundRequestOut.model_validate(refund) if refund else None
    detail.connected_transactions = incident_service.connected_transaction_count(db, incident)
    return detail


@router.get("/incidents", response_model=list[IncidentOut])
def list_incidents(
    user: User = Depends(current_user), db: Session = Depends(get_db)
) -> list[IncidentOut]:
    rows = db.scalars(
        select(Incident).where(Incident.user_id == user.id).order_by(Incident.created_at.desc())
    ).all()
    return [IncidentOut.model_validate(i) for i in rows]


@router.post("/incidents", response_model=IncidentDetailOut, status_code=status.HTTP_201_CREATED)
def create_incident(
    payload: IncidentCreate, user: User = Depends(current_user), db: Session = Depends(get_db)
) -> IncidentDetailOut:
    tx = None
    if payload.transaction_reference:
        tx = db.scalar(
            select(Transaction).where(
                Transaction.reference == payload.transaction_reference,
                Transaction.user_id == user.id,
            )
        )
        if tx is None:
            raise HTTPException(
                status.HTTP_404_NOT_FOUND, detail="No transaction with that reference."
            )

    refund = None
    if payload.refund_request_id:
        refund = db.scalar(
            select(RefundRequest).where(
                RefundRequest.id == payload.refund_request_id, RefundRequest.user_id == user.id
            )
        )

    risk_score = refund.risk_score if refund else (tx.risk_score if tx else 0)
    incident = incident_service.create_incident(
        db, user, tx, refund, risk_score,
        risk_level="CRITICAL" if risk_score >= 81 else "HIGH" if risk_score >= 61 else "MEDIUM",
        summary=payload.summary,
        scam_message=payload.scam_message,
        title=payload.title,
        potential_loss=payload.potential_loss or None,
    )
    if payload.suspect_handle:
        incident.suspect_handle = payload.suspect_handle
    if tx is not None:
        incident_service.build_timeline_from_transaction(db, incident, tx, refund)
    incident_service.seed_evidence_placeholders(db, incident, present=[])
    db.commit()
    db.refresh(incident)
    return _detail(db, incident)


@router.get("/incidents/{incident_id}", response_model=IncidentDetailOut)
def get_incident(
    incident_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)
) -> IncidentDetailOut:
    return _detail(db, _load(db, user, incident_id))


@router.patch("/incidents/{incident_id}", response_model=IncidentDetailOut)
def update_incident(
    incident_id: int,
    payload: IncidentUpdate,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> IncidentDetailOut:
    incident = _load(db, user, incident_id)
    changes = payload.model_dump(exclude_unset=True)
    if "status" in changes and changes["status"] != incident.status:
        incident_service.add_event(
            db, incident, f"Status changed to {changes['status'].replace('_', ' ').title()}",
            source="USER",
        )
    for field, value in changes.items():
        setattr(incident, field, value)
    db.commit()
    db.refresh(incident)
    return _detail(db, incident)


@router.get("/incidents/{incident_id}/evidence", response_model=list[EvidenceOut])
def incident_evidence(
    incident_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)
) -> list[EvidenceOut]:
    incident = _load(db, user, incident_id)
    return [EvidenceOut.model_validate(e) for e in incident.evidence]


# ---------------------------------------------------------------- reports
report_router = APIRouter(prefix="/api/reports", tags=["reports"])


@report_router.get("", response_model=list[ReportOut])
def list_reports(user: User = Depends(current_user), db: Session = Depends(get_db)) -> list[ReportOut]:
    rows = db.scalars(
        select(Report).where(Report.user_id == user.id).order_by(Report.generated_at.desc())
    ).all()
    return [ReportOut.model_validate(r) for r in rows]


@report_router.post("/generate", response_model=ReportOut, status_code=status.HTTP_201_CREATED)
def generate_report(
    payload: ReportGenerateRequest,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> ReportOut:
    incident = _load(db, user, payload.incident_id)
    report = report_service.generate(db, incident, include_package=payload.include_package)
    db.commit()
    db.refresh(report)
    return ReportOut.model_validate(report)


@report_router.get("/{report_id}", response_model=ReportOut)
def get_report(
    report_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)
) -> ReportOut:
    report = db.scalar(select(Report).where(Report.id == report_id, Report.user_id == user.id))
    if report is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="No report with that id.")
    return ReportOut.model_validate(report)


@report_router.get("/{report_id}/pdf")
def download_pdf(
    report_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)
) -> FileResponse:
    from app.config import settings

    report = db.scalar(select(Report).where(Report.id == report_id, Report.user_id == user.id))
    if report is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="No report with that id.")
    path = settings.reports_dir / report.pdf_filename
    if not path.exists():
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="The report file is no longer on disk.")
    return FileResponse(path, filename=report.pdf_filename, media_type="application/pdf")


@report_router.get("/{report_id}/package")
def download_package(
    report_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)
) -> FileResponse:
    from app.config import settings

    report = db.scalar(select(Report).where(Report.id == report_id, Report.user_id == user.id))
    if report is None or not report.package_filename:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="No evidence package for that report.")
    path = settings.reports_dir / report.package_filename
    if not path.exists():
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="The package file is no longer on disk.")
    return FileResponse(path, filename=report.package_filename, media_type="application/zip")

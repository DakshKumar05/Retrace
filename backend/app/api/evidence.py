from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import current_user
from app.database import get_db
from app.models import EVIDENCE_CATEGORIES, Evidence, Incident, User
from app.schemas import EvidenceCompleteness, EvidenceOut
from app.services import evidence_service, incident_service

router = APIRouter(prefix="/api/evidence", tags=["evidence"])


@router.get("/categories")
def categories() -> dict:
    return {"categories": EVIDENCE_CATEGORIES}


@router.get("", response_model=list[EvidenceOut])
def list_evidence(
    incident_id: int | None = Query(None),
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> list[EvidenceOut]:
    stmt = select(Evidence).where(Evidence.user_id == user.id)
    if incident_id is not None:
        stmt = stmt.where(Evidence.incident_id == incident_id)
    rows = db.scalars(stmt.order_by(Evidence.placeholder, Evidence.uploaded_at.desc())).all()
    return [EvidenceOut.model_validate(r) for r in rows]


@router.get("/completeness", response_model=EvidenceCompleteness)
def completeness(
    incident_id: int | None = Query(None),
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> EvidenceCompleteness:
    return EvidenceCompleteness(**incident_service.completeness(db, incident_id, user.id))


@router.post("/upload", response_model=EvidenceOut, status_code=status.HTTP_201_CREATED)
def upload(
    file: UploadFile = File(...),
    evidence_type: str = Form("supporting_document"),
    label: str | None = Form(None),
    description: str | None = Form(None),
    incident_id: int | None = Form(None),
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> EvidenceOut:
    """Preserve a file exactly as supplied and record its SHA-256 fingerprint."""
    known_types = {t for kinds in EVIDENCE_CATEGORIES.values() for t in kinds}
    if evidence_type not in known_types:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown evidence type. Choose one of: {', '.join(sorted(known_types))}.",
        )

    incident = None
    if incident_id is not None:
        incident = db.scalar(
            select(Incident).where(Incident.id == incident_id, Incident.user_id == user.id)
        )
        if incident is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="No case with that id.")

    stored_name, sha256, size = evidence_service.store(file, user.id)
    original = evidence_service.safe_filename(file.filename or stored_name)

    # If a placeholder already exists for this type, fill it in rather than duplicating the row.
    record = None
    if incident is not None:
        record = db.scalar(
            select(Evidence).where(
                Evidence.incident_id == incident.id,
                Evidence.evidence_type == evidence_type,
                Evidence.placeholder.is_(True),
            )
        )
    if record is None:
        record = Evidence(
            user_id=user.id,
            incident_id=incident.id if incident else None,
            evidence_type=evidence_type,
            category=evidence_service.category_for_type(evidence_type),
        )
        db.add(record)

    record.label = label or incident_service.EVIDENCE_LABELS.get(
        evidence_type, evidence_type.replace("_", " ").title()
    )
    record.category = evidence_service.category_for_type(evidence_type)
    record.original_filename = original
    record.stored_filename = stored_name
    record.content_type = file.content_type
    record.size_bytes = size
    record.sha256 = sha256
    record.placeholder = False
    record.description = description

    if incident is not None:
        incident_service.add_event(
            db, incident, f"Evidence added: {record.label}",
            f"SHA-256 {sha256[:12]}… recorded at intake.", source="EVIDENCE",
        )

    db.commit()
    db.refresh(record)
    return EvidenceOut.model_validate(record)


@router.get("/{evidence_id}", response_model=EvidenceOut)
def get_evidence(
    evidence_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)
) -> EvidenceOut:
    item = db.scalar(
        select(Evidence).where(Evidence.id == evidence_id, Evidence.user_id == user.id)
    )
    if item is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="No evidence with that id.")
    return EvidenceOut.model_validate(item)


@router.get("/{evidence_id}/verify")
def verify(
    evidence_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)
) -> dict:
    """Re-hash the stored file and compare it with the fingerprint taken at intake."""
    item = db.scalar(
        select(Evidence).where(Evidence.id == evidence_id, Evidence.user_id == user.id)
    )
    if item is None or not item.stored_filename:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="No stored file for that id.")
    matches = evidence_service.verify_hash(item.stored_filename, item.sha256)
    return {"evidence_id": item.id, "sha256": item.sha256, "unchanged": matches}


@router.get("/{evidence_id}/download")
def download(
    evidence_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)
) -> FileResponse:
    item = db.scalar(
        select(Evidence).where(Evidence.id == evidence_id, Evidence.user_id == user.id)
    )
    if item is None or not item.stored_filename:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="No stored file for that id.")
    return FileResponse(
        evidence_service.path_for(item.stored_filename),
        filename=item.original_filename or item.stored_filename,
        media_type=item.content_type or "application/octet-stream",
    )


@router.delete("/{evidence_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_evidence(
    evidence_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)
) -> None:
    item = db.scalar(
        select(Evidence).where(Evidence.id == evidence_id, Evidence.user_id == user.id)
    )
    if item is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="No evidence with that id.")
    db.delete(item)
    db.commit()

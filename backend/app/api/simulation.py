from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import current_user
from app.database import get_db
from app.models import User
from app.schemas import (
    EvidenceCompleteness,
    IncidentOut,
    RefundRequestOut,
    SimulationRequest,
    SimulationResponse,
    SimulationStep,
    TransactionOut,
)
from app.services import simulation_service

router = APIRouter(prefix="/api/simulation", tags=["simulation"])


@router.post("/scam", response_model=SimulationResponse)
def simulate_scam(
    payload: SimulationRequest,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> SimulationResponse:
    """Play out the full accidental-transfer scam against synthetic data."""
    result = simulation_service.run(db, user, unsafe=payload.unsafe)
    return SimulationResponse(
        transaction=TransactionOut.model_validate(result["transaction"]),
        refund_request=RefundRequestOut.model_validate(result["refund_request"]),
        analysis=result["analysis"],
        steps=[SimulationStep(**s) for s in result["steps"]],
        incident=IncidentOut.model_validate(result["incident"]) if result["incident"] else None,
        completeness=(
            EvidenceCompleteness(**result["completeness"]) if result["completeness"] else None
        ),
        safe_mode_enabled=result["safe_mode_enabled"],
    )


@router.post("/reset")
def reset_demo(user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    """Restore the seeded demo state so the walkthrough can be run again."""
    simulation_service.reset(db, user)
    return {"status": "reset", "message": "Demo data restored."}

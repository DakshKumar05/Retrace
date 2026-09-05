"""Retrace API.

A prototype payment-risk and incident-response service for refund-abuse scams.
It never moves real money and never asks for a UPI PIN, OTP, bank password or
card CVV.
"""
from __future__ import annotations

import logging

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import (
    admin,
    auth,
    evidence,
    incidents,
    lab,
    payments,
    refunds,
    risk,
    simulation,
    transactions,
)
from app.config import settings
from app.database import SessionLocal, init_db

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s - %(message)s"
)
log = logging.getLogger("retrace")

app = FastAPI(
    title=settings.app_name,
    version=settings.version,
    description=(
        "Refund safety scoring, incident capture and evidence packaging for the "
        "accidental-transfer refund scam. Prototype built on synthetic data."
    ),
    docs_url="/docs",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

for router in (
    auth.router,
    transactions.router,
    risk.router,
    refunds.router,
    evidence.router,
    incidents.router,
    incidents.report_router,
    admin.router,
    simulation.router,
    lab.router,
    payments.router,
    payments.webhook_router,
):
    app.include_router(router)


@app.exception_handler(RequestValidationError)
async def validation_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Return the first problem in plain language instead of a nested error tree."""
    first = exc.errors()[0] if exc.errors() else {}
    field = ".".join(str(p) for p in first.get("loc", [])[1:]) or "request"
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": f"{field}: {first.get('msg', 'is not valid')}"},
    )


@app.on_event("startup")
def on_startup() -> None:
    init_db()
    if settings.auto_seed:
        from app.database.seed import run as seed

        db = SessionLocal()
        try:
            seed(db)
        except Exception as exc:  # pragma: no cover - seeding must never block boot
            db.rollback()
            log.warning("Seeding skipped: %s", exc)
        finally:
            db.close()
    log.info("Retrace API ready in %s mode", settings.environment)


@app.get("/api/health", tags=["meta"])
def health() -> dict:
    return {
        "status": "ok",
        "version": settings.version,
        "environment": settings.environment,
        "database": settings.database_url.split("://")[0],
        "refund_mode": "RAZORPAY_TEST_MODE" if settings.razorpay_test_mode else "SIMULATED",
    }


@app.get("/api/privacy", tags=["meta"])
def privacy() -> dict:
    return {
        "summary": "Retrace handles financial and personal evidence, so it collects as little as possible.",
        "points": [
            "Every transaction, balance and refund in this build is synthetic. No real money moves.",
            "Retrace never asks for a UPI PIN, OTP, bank password, card CVV or net-banking login.",
            "Upload evidence only when you actually need it in a case. You can delete any file.",
            "Uploaded files are stored on the server running this app and are never sent anywhere else.",
            "Files are stored exactly as received. Retrace records a SHA-256 fingerprint instead of editing them.",
            "Passwords are hashed with bcrypt and are never written to logs.",
        ],
        "report_disclaimer": (
            "The Incident & Evidence Report is a structured summary, not an official police "
            "report, legal opinion or determination of fraud."
        ),
    }

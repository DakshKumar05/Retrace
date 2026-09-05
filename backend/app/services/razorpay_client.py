"""Razorpay Test Mode client.

Only ``rzp_test_`` keys are ever accepted; a live key disables the integration
rather than risking a real rupee.

The refund call is the one that matters to this product. ``POST
/v1/payments/:id/refund`` returns money to the instrument that paid, and the
caller cannot name a destination. The refund scam only works when the victim
steps off that rail and sends a fresh transfer to a handle the scammer chose,
so routing through this API is what "Safe Refund" actually means here.
"""
from __future__ import annotations

import hashlib
import hmac
import logging

import httpx

from app.config import settings

log = logging.getLogger("retrace.razorpay")

API_BASE = "https://api.razorpay.com/v1"
TIMEOUT = httpx.Timeout(15.0, connect=8.0)


class RazorpayError(RuntimeError):
    """A Razorpay API call failed. Carries the provider's own description."""

    def __init__(self, message: str, *, status_code: int | None = None, code: str | None = None):
        super().__init__(message)
        self.status_code = status_code
        self.code = code


def enabled() -> bool:
    """True only when a usable test key pair is configured."""
    return bool(settings.razorpay_test_mode and settings.razorpay_key_secret)


def _auth() -> tuple[str, str]:
    if not enabled():
        raise RazorpayError("Razorpay Test Mode is not configured.")
    return (settings.razorpay_key_id or "", settings.razorpay_key_secret or "")


def _to_paise(amount_inr: float) -> int:
    return int(round(float(amount_inr) * 100))


def _request(method: str, path: str, payload: dict | None = None) -> dict:
    url = f"{API_BASE}{path}"
    try:
        with httpx.Client(timeout=TIMEOUT) as client:
            response = client.request(method, url, json=payload, auth=_auth())
    except httpx.HTTPError as exc:
        raise RazorpayError(f"Could not reach Razorpay: {exc}") from exc

    try:
        body = response.json()
    except ValueError:
        body = {}

    if response.status_code >= 400:
        error = body.get("error", {}) if isinstance(body, dict) else {}
        raise RazorpayError(
            error.get("description") or f"Razorpay returned HTTP {response.status_code}.",
            status_code=response.status_code,
            code=error.get("code"),
        )
    return body


def create_order(amount_inr: float, receipt: str, notes: dict | None = None) -> dict:
    """Create a test-mode order so Checkout can collect a real test payment."""
    return _request(
        "POST",
        "/orders",
        {
            "amount": _to_paise(amount_inr),
            "currency": "INR",
            "receipt": receipt[:40],
            "notes": notes or {},
        },
    )


def fetch_payment(payment_id: str) -> dict:
    return _request("GET", f"/payments/{payment_id}")


def create_refund(
    payment_id: str, amount_inr: float | None = None, notes: dict | None = None
) -> dict:
    """Refund a payment to its source. There is no destination parameter by design."""
    payload: dict = {"speed": "normal", "notes": notes or {}}
    if amount_inr is not None:
        payload["amount"] = _to_paise(amount_inr)
    return _request("POST", f"/payments/{payment_id}/refund", payload)


def fetch_refund(refund_id: str) -> dict:
    return _request("GET", f"/refunds/{refund_id}")


def verify_checkout_signature(order_id: str, payment_id: str, signature: str) -> bool:
    """Confirm a Checkout callback really came from Razorpay."""
    secret = settings.razorpay_key_secret
    if not secret or not signature:
        return False
    expected = hmac.new(
        secret.encode(), f"{order_id}|{payment_id}".encode(), hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


def verify_webhook_signature(raw_body: bytes, signature: str) -> bool:
    """Validate X-Razorpay-Signature against the raw, unparsed request body."""
    secret = settings.razorpay_webhook_secret
    if not secret or not signature:
        return False
    expected = hmac.new(secret.encode(), raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)

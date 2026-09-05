"""Evidence intake.

Uploaded bytes are written once, hashed, and never rewritten. All derived
information lives in the database so the original file stays untouched.
"""
from __future__ import annotations

import hashlib
import re
import secrets
from pathlib import Path

from fastapi import HTTPException, UploadFile, status

from app.config import settings
from app.models import EVIDENCE_CATEGORIES

_SAFE_NAME = re.compile(r"[^A-Za-z0-9._-]+")
_CHUNK = 1024 * 256


def category_for_type(evidence_type: str) -> str:
    for category, kinds in EVIDENCE_CATEGORIES.items():
        if evidence_type in kinds:
            return category
    return "OTHER"


def safe_filename(name: str) -> str:
    """Strip directories and anything that is not a plain filename character."""
    base = Path(name or "evidence").name
    base = _SAFE_NAME.sub("_", base).strip("._") or "evidence"
    return base[:120]


def validate(upload: UploadFile) -> str:
    suffix = Path(upload.filename or "").suffix.lower()
    if suffix not in settings.allowed_upload_extensions:
        allowed = ", ".join(sorted(settings.allowed_upload_extensions))
        raise HTTPException(
            status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"{suffix or 'This file type'} is not accepted. Allowed types: {allowed}.",
        )
    return suffix


def store(upload: UploadFile, user_id: int) -> tuple[str, str, int]:
    """Write the upload to disk, streaming, and return (stored name, sha256, size)."""
    suffix = validate(upload)
    stored_name = f"u{user_id}_{secrets.token_hex(8)}{suffix}"
    target = settings.evidence_dir / stored_name

    digest = hashlib.sha256()
    size = 0
    upload.file.seek(0)
    try:
        with target.open("wb") as out:
            while chunk := upload.file.read(_CHUNK):
                size += len(chunk)
                if size > settings.max_upload_bytes:
                    raise HTTPException(
                        status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail=(
                            "File is larger than the "
                            f"{settings.max_upload_bytes // (1024 * 1024)} MB limit."
                        ),
                    )
                digest.update(chunk)
                out.write(chunk)
    except HTTPException:
        target.unlink(missing_ok=True)
        raise
    except OSError as exc:
        target.unlink(missing_ok=True)
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Could not save the file.") from exc

    if size == 0:
        target.unlink(missing_ok=True)
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="The file is empty.")

    return stored_name, digest.hexdigest(), size


def path_for(stored_filename: str) -> Path:
    """Resolve a stored file, refusing anything that escapes the evidence directory."""
    candidate = (settings.evidence_dir / Path(stored_filename).name).resolve()
    root = settings.evidence_dir.resolve()
    if root not in candidate.parents and candidate != root:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Invalid file reference.")
    if not candidate.exists():
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="The stored file is no longer available.")
    return candidate


def verify_hash(stored_filename: str, expected: str | None) -> bool:
    """Re-hash a stored file to confirm it has not changed since intake."""
    if not expected:
        return False
    digest = hashlib.sha256()
    with path_for(stored_filename).open("rb") as handle:
        while chunk := handle.read(_CHUNK):
            digest.update(chunk)
    return digest.hexdigest() == expected

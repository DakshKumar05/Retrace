"""Application configuration, driven entirely by environment variables."""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


def _bool(name: str, default: bool = False) -> bool:
    return os.getenv(name, str(default)).strip().lower() in {"1", "true", "yes", "on"}


class Settings:
    """Runtime settings. No secrets are ever hard-coded here."""

    def __init__(self) -> None:
        self.app_name: str = "Retrace API"
        self.version: str = "1.0.0"
        self.environment: str = os.getenv("ENVIRONMENT", "development")

        # Defaults to SQLite so the project runs with zero infrastructure.
        # docker-compose supplies a PostgreSQL URL instead.
        self.database_url: str = os.getenv(
            "DATABASE_URL", f"sqlite:///{BASE_DIR / 'retrace.db'}"
        )

        self.jwt_secret: str = os.getenv("JWT_SECRET", "dev-only-insecure-secret-change-me")
        self.jwt_algorithm: str = os.getenv("JWT_ALGORITHM", "HS256")
        self.jwt_expire_minutes: int = int(os.getenv("JWT_EXPIRE_MINUTES", "720"))

        self.cors_origins: list[str] = [
            o.strip()
            for o in os.getenv(
                "CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
            ).split(",")
            if o.strip()
        ]

        self.storage_dir: Path = Path(os.getenv("STORAGE_DIR", str(BASE_DIR / "storage")))
        self.evidence_dir: Path = self.storage_dir / "evidence"
        self.reports_dir: Path = self.storage_dir / "reports"

        self.max_upload_bytes: int = int(os.getenv("MAX_UPLOAD_MB", "15")) * 1024 * 1024
        self.allowed_upload_extensions: set[str] = {
            ".pdf", ".png", ".jpg", ".jpeg", ".webp", ".txt", ".csv", ".eml", ".mp3", ".m4a", ".ogg",
        }

        self.auto_seed: bool = _bool("AUTO_SEED", True)
        self.demo_email: str = os.getenv("DEMO_EMAIL", "demo@retrace.com")
        self.demo_password: str = os.getenv("DEMO_PASSWORD", "Demo@123")

        # Razorpay Test Mode. Absent keys simply mean the refund flow stays simulated.
        self.razorpay_key_id: str | None = os.getenv("RAZORPAY_KEY_ID") or None
        self.razorpay_key_secret: str | None = os.getenv("RAZORPAY_KEY_SECRET") or None
        self.razorpay_webhook_secret: str | None = os.getenv("RAZORPAY_WEBHOOK_SECRET") or None

        self.evidence_dir.mkdir(parents=True, exist_ok=True)
        self.reports_dir.mkdir(parents=True, exist_ok=True)

    @property
    def razorpay_test_mode(self) -> bool:
        """True only when a *test* key is configured. Live keys are refused."""
        return bool(self.razorpay_key_id and self.razorpay_key_id.startswith("rzp_test_"))


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

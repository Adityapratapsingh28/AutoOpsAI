"""
AutoOps AI — Configuration Module.

Loads all environment variables and provides a centralized Settings object
used across the entire backend application.
"""

import os
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".env"))


class Settings:
    """Application-wide configuration loaded from environment variables."""

    # ── Database ──
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql://postgres:postgres@localhost:5432/autoops"
    )

    # ── JWT Auth ──
    JWT_SECRET: str = os.getenv("JWT_SECRET", "autoops-super-secret-change-me")
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRY_HOURS: int = int(os.getenv("JWT_EXPIRY_HOURS", "24"))

    # ── Google OAuth ──
    GOOGLE_CLIENT_ID: str = os.getenv("GOOGLE_CLIENT_ID", "")

    # ── Redis Cache ──
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379")

    # ── LLM ──
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    LLM_MODEL: str = os.getenv("LLM_MODEL", "llama-3.3-70b-versatile")

    # ── SMTP (Email Tool) ──
    SMTP_HOST: str = os.getenv("SMTP_HOST", "smtp.gmail.com")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USER: str = os.getenv("SMTP_USER", "")
    SMTP_PASS: str = os.getenv("SMTP_PASS", "")

    # ── Slack ──
    SLACK_BOT_TOKEN: str = os.getenv("SLACK_BOT_TOKEN", "")

    # ── Zoom (Server-to-Server OAuth) ──
    ZOOM_ACCOUNT_ID: str = os.getenv("ZOOM_ACCOUNT_ID", "").strip()
    ZOOM_CLIENT_ID: str = os.getenv("ZOOM_CLIENT_ID", "").strip()
    ZOOM_CLIENT_SECRET: str = os.getenv("ZOOM_CLIENT_SECRET", "").strip()

    # ── File Uploads ──
    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", os.path.join(
        os.path.dirname(__file__), "..", "..", "uploads"
    ))

    # ── Core Engine Path (READ-ONLY) ──
    CORE_ENGINE_PATH: str = os.getenv("CORE_ENGINE_PATH", os.path.join(
        os.path.dirname(__file__), "..", "..", "..",
        "ODI-based-multi-agent-Framework"
    ))


settings = Settings()

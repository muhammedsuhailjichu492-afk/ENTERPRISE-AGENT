"""
Centralized configuration for the Autonomous Enterprise Intelligence & Operations Agent.

All environment-driven settings live here so the rest of the codebase never
touches os.environ directly.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from project root regardless of current working directory
PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")


class Settings:
    # --- LLM ---
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
    ANTHROPIC_MODEL: str = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-5")

    # --- Risk / approval ---
    RISK_APPROVAL_THRESHOLD: int = int(os.getenv("RISK_APPROVAL_THRESHOLD", "55"))

    # --- Storage ---
    DATABASE_PATH: str = os.getenv("DATABASE_PATH", str(PROJECT_ROOT / "data" / "enterprise.db"))
    CHROMA_PATH: str = os.getenv("CHROMA_PATH", str(PROJECT_ROOT / "data" / "chroma"))

    # --- Server ---
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))

    # --- Domains the platform understands (mirrors the architecture diagram) ---
    DOMAINS = [
        "production",
        "inventory",
        "quality",
        "operations",
        "procurement",
        "hr",
        "sales",
        "finance",
        "projects",
        "reporting",
    ]

    def ensure_dirs(self) -> None:
        Path(self.DATABASE_PATH).parent.mkdir(parents=True, exist_ok=True)
        Path(self.CHROMA_PATH).mkdir(parents=True, exist_ok=True)

    @property
    def llm_enabled(self) -> bool:
        return bool(self.ANTHROPIC_API_KEY and self.ANTHROPIC_API_KEY != "your_api_key_here")


settings = Settings()
settings.ensure_dirs()

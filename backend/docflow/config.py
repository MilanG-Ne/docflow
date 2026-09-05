import os
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    database_url: str = field(
        default_factory=lambda: os.getenv("DATABASE_URL", "sqlite:///./data/docflow.db")
    )
    artifact_dir: Path = field(
        default_factory=lambda: Path(os.getenv("ARTIFACT_DIR", "./data/artifacts"))
    )
    frontend_dir: Path = field(
        default_factory=lambda: Path(os.getenv("FRONTEND_DIR", "../frontend/dist/client"))
    )
    origin: str = field(default_factory=lambda: os.getenv("APP_ORIGIN", "http://localhost:8000"))
    cookie_secure: bool = field(
        default_factory=lambda: os.getenv("COOKIE_SECURE", "false").lower() == "true"
    )
    demo_mode: bool = field(
        default_factory=lambda: os.getenv("DEMO_MODE", "false").lower() == "true"
    )
    libreoffice_bin: str = field(
        default_factory=lambda: os.getenv("LIBREOFFICE_BIN", "libreoffice")
    )
    template_path: Path = Path(__file__).parent / "templates" / "proposal-v1.docx"

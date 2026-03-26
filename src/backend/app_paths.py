from __future__ import annotations

import sys
from pathlib import Path


def project_root() -> Path:
    """Return the project or bundled application root directory."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[2]


def app_data_dir() -> Path:
    """Return the persistent application data directory and ensure it exists."""
    path = Path.home() / "Documents" / "SaveSync"
    path.mkdir(parents=True, exist_ok=True)
    return path


def app_config_path() -> Path:
    """Return the JSON configuration file path."""
    return app_data_dir() / "profiles.json"


def credentials_path() -> Path:
    """Return the cached Google OAuth credentials file path."""
    return app_data_dir() / "mycreds.txt"


def client_secrets_path(base_dir: Path | None = None) -> Path:
    """Return the client secrets path, preferring an explicit base directory."""
    root = base_dir or project_root()
    return root / "client_secrets.json"

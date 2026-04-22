from __future__ import annotations

import json
from pathlib import Path

from .app_paths import app_config_path
from .models import AppConfig


class ConfigStore:
    """Load and persist the application's JSON configuration."""

    def __init__(self, *, config_path: Path | None = None) -> None:
        self.config_path = config_path or app_config_path()

    def load(self) -> AppConfig:
        """Load JSON config or return an empty config on first run."""
        if self.config_path.exists():
            payload = json.loads(self.config_path.read_text(encoding="utf-8"))
            return AppConfig.from_dict(payload)
        return AppConfig()

    def save(self, config: AppConfig) -> None:
        """Validate and write the configuration to disk."""
        config.validate()
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        self.config_path.write_text(
            json.dumps(config.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

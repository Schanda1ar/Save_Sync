from __future__ import annotations

import json
from configparser import ConfigParser
from pathlib import Path

from .app_paths import app_config_path, legacy_config_path
from .models import AppConfig, GameProfile, ValidationError


class ConfigStore:
    def __init__(self, *, config_path: Path | None = None, base_dir: Path | None = None) -> None:
        self.base_dir = base_dir
        self.config_path = config_path or app_config_path()

    def load(self) -> AppConfig:
        if self.config_path.exists():
            payload = json.loads(self.config_path.read_text(encoding="utf-8"))
            return AppConfig.from_dict(payload)
        config = self._load_legacy_config()
        self.save(config)
        return config

    def save(self, config: AppConfig) -> None:
        config.validate()
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        self.config_path.write_text(
            json.dumps(config.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _load_legacy_config(self) -> AppConfig:
        legacy_path = legacy_config_path(self.base_dir)
        if not legacy_path.exists():
            return AppConfig()

        parser = ConfigParser()
        parser.read(legacy_path, encoding="utf-8")
        if "paths" not in parser:
            raise ValidationError("Legacy-Konfiguration enthält keinen 'paths'-Abschnitt.")

        section = parser["paths"]
        profile = GameProfile.create(
            profile_id="legacy-import",
            display_name="Legacy Game",
            game_exe_path=section.get("game_exe", ""),
            save_folder_path=section.get("save_file", ""),
            game_process_names=section.get("game_process_names", ""),
            drive_filename=self._legacy_drive_filename(section.get("drive_filename", "")),
            drive_folder_id=section.get("drive_folder_id", "").strip(),
        )
        return AppConfig(profiles=[profile], selected_profile_id=profile.id)

    def _legacy_drive_filename(self, value: str) -> str:
        filename = value.strip()
        if not filename:
            return "savegame.zip"
        if filename.lower().endswith(".zip"):
            return filename
        stem = Path(filename).stem or filename
        return f"{stem}.zip"

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any
from uuid import uuid4


class ValidationError(ValueError):
    """Raised when a profile or config payload is invalid."""


def _clean_string(value: Any, field_name: str, *, required: bool = True) -> str:
    if value is None:
        value = ""
    text = str(value).strip()
    if required and not text:
        raise ValidationError(f"'{field_name}' darf nicht leer sein.")
    return text


def normalize_process_names(value: Any) -> list[str]:
    if isinstance(value, str):
        names = [item.strip() for item in value.split(",")]
    elif isinstance(value, list):
        names = [str(item).strip() for item in value]
    else:
        raise ValidationError("'game_process_names' muss eine Liste oder CSV-Zeichenkette sein.")

    cleaned = [item for item in names if item]
    if not cleaned:
        raise ValidationError("'game_process_names' muss mindestens einen Prozessnamen enthalten.")
    return cleaned


@dataclass(slots=True)
class GameProfile:
    id: str
    display_name: str
    game_exe_path: str
    save_file_path: str
    game_process_names: list[str]
    drive_filename: str
    drive_folder_id: str = ""
    cloud_provider: str = "google_drive"

    @classmethod
    def create(
        cls,
        *,
        display_name: str,
        game_exe_path: str,
        save_file_path: str,
        game_process_names: list[str] | str,
        drive_filename: str,
        drive_folder_id: str = "",
        profile_id: str | None = None,
    ) -> "GameProfile":
        return cls.from_dict(
            {
                "id": profile_id or uuid4().hex,
                "display_name": display_name,
                "game_exe_path": game_exe_path,
                "save_file_path": save_file_path,
                "game_process_names": game_process_names,
                "drive_filename": drive_filename,
                "drive_folder_id": drive_folder_id,
                "cloud_provider": "google_drive",
            }
        )

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "GameProfile":
        profile = cls(
            id=_clean_string(payload.get("id"), "id"),
            display_name=_clean_string(payload.get("display_name"), "display_name"),
            game_exe_path=_clean_string(payload.get("game_exe_path"), "game_exe_path"),
            save_file_path=_clean_string(payload.get("save_file_path"), "save_file_path"),
            game_process_names=normalize_process_names(payload.get("game_process_names")),
            drive_filename=_clean_string(payload.get("drive_filename"), "drive_filename"),
            drive_folder_id=_clean_string(
                payload.get("drive_folder_id", ""),
                "drive_folder_id",
                required=False,
            ),
            cloud_provider=_clean_string(
                payload.get("cloud_provider", "google_drive"),
                "cloud_provider",
            ),
        )
        profile.validate()
        return profile

    def validate(self) -> None:
        if self.cloud_provider != "google_drive":
            raise ValidationError("Aktuell wird nur 'google_drive' unterstützt.")
        if not Path(self.game_exe_path).suffix:
            raise ValidationError("'game_exe_path' muss auf eine ausführbare Datei zeigen.")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class AppConfig:
    profiles: list[GameProfile] = field(default_factory=list)
    selected_profile_id: str = ""

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "AppConfig":
        raw_profiles = payload.get("profiles", [])
        if not isinstance(raw_profiles, list):
            raise ValidationError("'profiles' muss eine Liste sein.")

        profiles = [GameProfile.from_dict(item) for item in raw_profiles]
        config = cls(
            profiles=profiles,
            selected_profile_id=str(payload.get("selected_profile_id", "")).strip(),
        )
        config.validate()
        return config

    def validate(self) -> None:
        ids = [profile.id for profile in self.profiles]
        if len(ids) != len(set(ids)):
            raise ValidationError("Profil-IDs müssen eindeutig sein.")
        if self.selected_profile_id and self.selected_profile_id not in set(ids):
            raise ValidationError("Das ausgewählte Profil existiert nicht.")

    def to_dict(self) -> dict[str, Any]:
        return {
            "selected_profile_id": self.selected_profile_id,
            "profiles": [profile.to_dict() for profile in self.profiles],
        }

    def get_profile(self, profile_id: str) -> GameProfile | None:
        for profile in self.profiles:
            if profile.id == profile_id:
                return profile
        return None

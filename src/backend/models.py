from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path, PureWindowsPath
from typing import Any
from uuid import uuid4


class ValidationError(ValueError):
    """Raised when a profile or config payload is invalid."""


@dataclass(slots=True)
class ImportedSaveFolderPath:
    """Describe how an imported save-folder path was adapted for the local machine."""

    path: str
    was_rewritten: bool = False


def _clean_string(value: Any, field_name: str, *, required: bool = True) -> str:
    """Normalize scalar input to a stripped string and enforce required fields."""
    if value is None:
        value = ""
    text = str(value).strip()
    if required and not text:
        raise ValidationError(f"'{field_name}' darf nicht leer sein.")
    return text


def normalize_process_names(value: Any) -> list[str]:
    """Normalize process names from CSV or list input into a cleaned list."""
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


def normalize_save_folder_path(value: Any) -> str:
    """Normalize save locations while preserving non-existing directory names."""
    path_text = _clean_string(value, "save_folder_path")
    path = Path(path_text)

    if path.exists():
        if path.is_dir():
            return str(path)
        if path.is_file():
            return str(path.parent)
        raise ValidationError("'save_folder_path' muss auf einen Ordner zeigen.")

    return str(path)


def _current_user_home() -> Path:
    """Return the current user's home directory for import-time path adaptation."""
    return Path.home()


def adapt_imported_save_folder_path(value: Any) -> ImportedSaveFolderPath:
    """Rewrite imported Windows user-profile paths to the current local user when possible."""
    normalized_path = normalize_save_folder_path(value)
    imported_path = PureWindowsPath(normalized_path)
    imported_parts = imported_path.parts
    if len(imported_parts) < 4:
        return ImportedSaveFolderPath(path=normalized_path)

    if len(imported_path.drive) != 2 or not imported_path.drive.endswith(":"):
        return ImportedSaveFolderPath(path=normalized_path)

    if imported_parts[1].lower() != "users":
        return ImportedSaveFolderPath(path=normalized_path)

    current_home = PureWindowsPath(str(_current_user_home()))
    current_parts = current_home.parts
    if (
        len(current_parts) < 3
        or current_parts[1].lower() != "users"
        or len(current_home.drive) != 2
        or not current_home.drive.endswith(":")
    ):
        return ImportedSaveFolderPath(path=normalized_path)

    rewritten_path = current_home.joinpath(*imported_parts[3:])
    return ImportedSaveFolderPath(
        path=str(rewritten_path),
        was_rewritten=str(rewritten_path) != normalized_path,
    )


def normalize_drive_filename(value: Any) -> str:
    """Normalize the archive name to a non-empty `.zip` filename."""
    text = _clean_string(value, "drive_filename")
    stem = Path(text).stem if text.lower().endswith(".zip") else text
    stem = stem.strip().strip(".")
    if not stem:
        raise ValidationError("'drive_filename' darf nicht leer sein.")
    return f"{stem}.zip"


def is_steam_game_id(value: str) -> bool:
    """Return whether the launch target is a numeric Steam game id."""
    return value.isdigit()


@dataclass(slots=True)
class GameProfile:
    """Validated application profile for one game's sync configuration."""

    id: str
    display_name: str
    game_exe_path: str
    save_folder_path: str
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
        save_folder_path: str,
        game_process_names: list[str] | str,
        drive_filename: str,
        drive_folder_id: str = "",
        profile_id: str | None = None,
    ) -> "GameProfile":
        """Create a profile from user input and generate an id when needed."""
        return cls.from_dict(
            {
                "id": profile_id or uuid4().hex,
                "display_name": display_name,
                "game_exe_path": game_exe_path,
                "save_folder_path": save_folder_path,
                "game_process_names": game_process_names,
                "drive_filename": drive_filename,
                "drive_folder_id": drive_folder_id,
                "cloud_provider": "google_drive",
            }
        )

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "GameProfile":
        """Build and validate a profile from serialized data."""
        profile = cls(
            id=_clean_string(payload.get("id"), "id"),
            display_name=_clean_string(payload.get("display_name"), "display_name"),
            game_exe_path=_clean_string(payload.get("game_exe_path"), "game_exe_path"),
            save_folder_path=normalize_save_folder_path(payload.get("save_folder_path")),
            game_process_names=normalize_process_names(payload.get("game_process_names")),
            drive_filename=normalize_drive_filename(payload.get("drive_filename")),
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
        """Validate cross-field constraints that simple normalization cannot cover."""
        if self.cloud_provider != "google_drive":
            raise ValidationError("Aktuell wird nur 'google_drive' unterstützt.")
        if is_steam_game_id(self.game_exe_path):
            return
        if not Path(self.game_exe_path).suffix:
            raise ValidationError(
                "'game_exe_path' muss auf eine ausführbare Datei oder eine Steam-Spiel-ID zeigen."
            )

    def to_dict(self) -> dict[str, Any]:
        """Serialize the profile for JSON storage or export."""
        return asdict(self)


@dataclass(slots=True)
class AppConfig:
    """Persistent application configuration containing all profiles."""

    profiles: list[GameProfile] = field(default_factory=list)
    selected_profile_id: str = ""

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "AppConfig":
        """Build and validate the application configuration from JSON data."""
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
        """Ensure profile ids are unique and the selected id is valid."""
        ids = [profile.id for profile in self.profiles]
        if len(ids) != len(set(ids)):
            raise ValidationError("Profil-IDs müssen eindeutig sein.")
        if self.selected_profile_id and self.selected_profile_id not in set(ids):
            raise ValidationError("Das ausgewählte Profil existiert nicht.")

    def to_dict(self) -> dict[str, Any]:
        """Serialize the configuration to the stored JSON shape."""
        return {
            "selected_profile_id": self.selected_profile_id,
            "profiles": [profile.to_dict() for profile in self.profiles],
        }

    def get_profile(self, profile_id: str) -> GameProfile | None:
        """Return a profile by id or `None` when it does not exist."""
        for profile in self.profiles:
            if profile.id == profile_id:
                return profile
        return None

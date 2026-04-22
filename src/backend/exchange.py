from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from .models import GameProfile, ValidationError, adapt_imported_save_folder_path


@dataclass(slots=True)
class ImportProfilesResult:
    """Describe imported profiles and any local path adjustments applied during import."""

    profiles: list[GameProfile]
    rewritten_path_count: int = 0
    created_directory_count: int = 0
    unresolved_path_count: int = 0


def export_profiles(profiles: list[GameProfile], destination: Path) -> None:
    """Write profiles to a portable JSON export file."""
    payload = {"profiles": [profile.to_dict() for profile in profiles]}
    destination.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def import_profiles(
    source: Path,
    *,
    existing_profile_ids: set[str] | None = None,
    apply_save_folder_side_effects: bool = True,
) -> ImportProfilesResult:
    """Load profiles from JSON, validate IDs first, then optionally prepare local save paths."""
    try:
        payload = json.loads(source.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValidationError(f"Ungültige JSON-Datei: {exc.msg}") from exc

    raw_profiles = payload.get("profiles")
    if not isinstance(raw_profiles, list):
        raise ValidationError("'profiles' muss in der JSON-Datei als Liste vorhanden sein.")

    profiles = [GameProfile.from_dict(item) for item in raw_profiles]
    ids = [profile.id for profile in profiles]
    if len(ids) != len(set(ids)):
        raise ValidationError("Importdatei enthält doppelte Profil-IDs.")

    conflicting_ids = sorted(set(ids) & (existing_profile_ids or set()))
    if conflicting_ids:
        raise ValidationError(f"Profil-ID '{conflicting_ids[0]}' existiert bereits.")

    rewritten_path_count = 0

    for profile in profiles:
        imported_path = adapt_imported_save_folder_path(profile.save_folder_path)
        if imported_path.was_rewritten:
            profile.save_folder_path = imported_path.path
            rewritten_path_count += 1

    created_directory_count = 0
    unresolved_path_count = 0
    if apply_save_folder_side_effects:
        created_directory_count, unresolved_path_count = prepare_imported_save_folders(profiles)

    return ImportProfilesResult(
        profiles=profiles,
        rewritten_path_count=rewritten_path_count,
        created_directory_count=created_directory_count,
        unresolved_path_count=unresolved_path_count,
    )


def prepare_imported_save_folders(profiles: list[GameProfile]) -> tuple[int, int]:
    """Create only the last missing save-folder segment for imported profiles."""
    created_directory_count = 0
    unresolved_path_count = 0

    for profile in profiles:
        save_folder = Path(profile.save_folder_path)
        if save_folder.exists():
            continue
        if not save_folder.parent.is_dir():
            unresolved_path_count += 1
            continue
        try:
            save_folder.mkdir(exist_ok=True)
        except OSError:
            unresolved_path_count += 1
            continue
        created_directory_count += 1

    return created_directory_count, unresolved_path_count

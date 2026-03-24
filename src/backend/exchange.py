from __future__ import annotations

import json
from pathlib import Path

from .models import GameProfile, ValidationError


def export_profiles(profiles: list[GameProfile], destination: Path) -> None:
    payload = {"profiles": [profile.to_dict() for profile in profiles]}
    destination.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def import_profiles(source: Path) -> list[GameProfile]:
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
    return profiles

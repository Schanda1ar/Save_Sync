import json
from pathlib import Path

import pytest

from backend.exchange import export_profiles, import_profiles
from backend.models import GameProfile, ValidationError


def build_profile() -> GameProfile:
    return GameProfile.create(
        profile_id="game-1",
        display_name="Example Game",
        game_exe_path="C:/Games/Game.exe",
        save_file_path="C:/Saves/game.sav",
        game_process_names=["Game.exe"],
        drive_filename="game.sav",
        drive_folder_id="folder-1",
    )


def test_export_and_import_profiles_roundtrip(tmp_path: Path) -> None:
    target = tmp_path / "profiles.json"
    export_profiles([build_profile()], target)

    imported = import_profiles(target)

    assert len(imported) == 1
    assert imported[0].display_name == "Example Game"


def test_import_rejects_duplicate_ids(tmp_path: Path) -> None:
    target = tmp_path / "profiles.json"
    profile = build_profile().to_dict()
    target.write_text(json.dumps({"profiles": [profile, profile]}), encoding="utf-8")

    with pytest.raises(ValidationError):
        import_profiles(target)

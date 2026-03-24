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
        save_folder_path="C:/Saves/Game",
        game_process_names=["Game.exe"],
        drive_filename="game",
        drive_folder_id="folder-1",
    )


def test_export_and_import_profiles_roundtrip(tmp_path: Path) -> None:
    target = tmp_path / "profiles.json"
    export_profiles([build_profile()], target)

    imported = import_profiles(target)

    assert len(imported) == 1
    assert imported[0].display_name == "Example Game"
    assert imported[0].save_folder_path == str(Path("C:/Saves/Game"))
    assert imported[0].drive_filename == "game.zip"


def test_import_rejects_duplicate_ids(tmp_path: Path) -> None:
    target = tmp_path / "profiles.json"
    profile = build_profile().to_dict()
    target.write_text(json.dumps({"profiles": [profile, profile]}), encoding="utf-8")

    with pytest.raises(ValidationError):
        import_profiles(target)


def test_import_supports_legacy_save_file_path_field(tmp_path: Path) -> None:
    target = tmp_path / "profiles.json"
    target.write_text(
        json.dumps(
            {
                "profiles": [
                    {
                        "id": "legacy",
                        "display_name": "Legacy Game",
                        "game_exe_path": "C:/Games/Game.exe",
                        "save_file_path": "C:/Saves/Game/save.sav",
                        "game_process_names": ["Game.exe"],
                        "drive_filename": "legacy.zip",
                        "drive_folder_id": "folder-1",
                        "cloud_provider": "google_drive",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    imported = import_profiles(target)

    assert imported[0].save_folder_path == str(Path("C:/Saves/Game"))


def test_import_normalizes_drive_filename_without_zip(tmp_path: Path) -> None:
    target = tmp_path / "profiles.json"
    target.write_text(
        json.dumps(
            {
                "profiles": [
                    {
                        "id": "plain-name",
                        "display_name": "Example Game",
                        "game_exe_path": "C:/Games/Game.exe",
                        "save_folder_path": "C:/Saves/Game",
                        "game_process_names": ["Game.exe"],
                        "drive_filename": "manual_backup",
                        "drive_folder_id": "",
                        "cloud_provider": "google_drive",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    imported = import_profiles(target)

    assert imported[0].drive_filename == "manual_backup.zip"


def test_import_accepts_numeric_steam_id_as_launch_target(tmp_path: Path) -> None:
    target = tmp_path / "profiles.json"
    target.write_text(
        json.dumps(
            {
                "profiles": [
                    {
                        "id": "steam-game",
                        "display_name": "Steam Game",
                        "game_exe_path": "2646460",
                        "save_folder_path": "C:/Saves/Game",
                        "game_process_names": ["Game.exe"],
                        "drive_filename": "steam_backup",
                        "drive_folder_id": "",
                        "cloud_provider": "google_drive",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    imported = import_profiles(target)

    assert imported[0].game_exe_path == "2646460"

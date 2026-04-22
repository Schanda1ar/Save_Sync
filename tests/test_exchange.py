import json
from pathlib import Path, PureWindowsPath

import pytest

import backend.models as models_module
from backend.exchange import export_profiles, import_profiles, prepare_imported_save_folders
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
    save_folder = tmp_path / "save"
    export_profiles(
        [
            GameProfile.create(
                profile_id="game-1",
                display_name="Example Game",
                game_exe_path="C:/Games/Game.exe",
                save_folder_path=str(save_folder),
                game_process_names=["Game.exe"],
                drive_filename="game",
                drive_folder_id="folder-1",
            )
        ],
        target,
    )

    imported = import_profiles(target)

    assert len(imported.profiles) == 1
    assert imported.profiles[0].display_name == "Example Game"
    assert imported.profiles[0].save_folder_path == str(save_folder)
    assert imported.profiles[0].drive_filename == "game.zip"
    assert imported.rewritten_path_count == 0
    assert imported.created_directory_count == 1
    assert imported.unresolved_path_count == 0
    assert save_folder.is_dir()


def test_import_rejects_duplicate_ids(tmp_path: Path) -> None:
    target = tmp_path / "profiles.json"
    profile = GameProfile.create(
        profile_id="game-1",
        display_name="Example Game",
        game_exe_path="C:/Games/Game.exe",
        save_folder_path=str(tmp_path / "save"),
        game_process_names=["Game.exe"],
        drive_filename="game",
        drive_folder_id="folder-1",
    ).to_dict()
    target.write_text(json.dumps({"profiles": [profile, profile]}), encoding="utf-8")

    with pytest.raises(ValidationError):
        import_profiles(target)

    assert not Path(profile["save_folder_path"]).exists()


def test_import_requires_save_folder_path_field(tmp_path: Path) -> None:
    target = tmp_path / "profiles.json"
    target.write_text(
        json.dumps(
            {
                "profiles": [
                    {
                        "id": "missing-save-folder",
                        "display_name": "Example Game",
                        "game_exe_path": "C:/Games/Game.exe",
                        "save_file_path": "C:/Saves/Game/save.sav",
                        "game_process_names": ["Game.exe"],
                        "drive_filename": "example.zip",
                        "drive_folder_id": "folder-1",
                        "cloud_provider": "google_drive",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValidationError, match="save_folder_path"):
        import_profiles(target)


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
                        "save_folder_path": str(tmp_path / "save"),
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

    assert imported.profiles[0].drive_filename == "manual_backup.zip"


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
                        "save_folder_path": str(tmp_path / "save"),
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

    assert imported.profiles[0].game_exe_path == "2646460"


def test_import_rewrites_windows_user_profile_path_to_current_user(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(models_module, "_current_user_home", lambda: Path(r"C:\Users\CurrentUser"))
    target = tmp_path / "profiles.json"
    target.write_text(
        json.dumps(
            {
                "profiles": [
                    {
                        "id": "portable-path",
                        "display_name": "Portable Game",
                        "game_exe_path": "C:/Games/Game.exe",
                        "save_folder_path": r"C:\Users\OtherUser\AppData\Local\Game\Saves",
                        "game_process_names": ["Game.exe"],
                        "drive_filename": "portable_save",
                        "drive_folder_id": "",
                        "cloud_provider": "google_drive",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    imported = import_profiles(target)

    assert imported.profiles[0].save_folder_path == str(
        PureWindowsPath(r"C:\Users\CurrentUser\AppData\Local\Game\Saves")
    )
    assert imported.rewritten_path_count == 1
    assert imported.created_directory_count == 0
    assert imported.unresolved_path_count == 1


def test_import_does_not_rewrite_unc_paths(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(models_module, "_current_user_home", lambda: Path(r"C:\Users\CurrentUser"))
    target = tmp_path / "profiles.json"
    unc_path = r"\\server\share\Users\OtherUser\AppData\Local\Game\Saves"
    target.write_text(
        json.dumps(
            {
                "profiles": [
                    {
                        "id": "unc-path",
                        "display_name": "Portable Game",
                        "game_exe_path": "C:/Games/Game.exe",
                        "save_folder_path": unc_path,
                        "game_process_names": ["Game.exe"],
                        "drive_filename": "portable_save",
                        "drive_folder_id": "",
                        "cloud_provider": "google_drive",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    imported = import_profiles(target)

    assert imported.profiles[0].save_folder_path == unc_path
    assert imported.rewritten_path_count == 0


def test_import_creates_target_directory_when_only_last_segment_is_missing(
    tmp_path: Path,
) -> None:
    target = tmp_path / "profiles.json"
    save_folder = tmp_path / "existing_parent" / "save"
    save_folder.parent.mkdir()
    target.write_text(
        json.dumps(
            {
                "profiles": [
                    {
                        "id": "create-last-segment",
                        "display_name": "Folder Game",
                        "game_exe_path": "C:/Games/Game.exe",
                        "save_folder_path": str(save_folder),
                        "game_process_names": ["Game.exe"],
                        "drive_filename": "folder_save",
                        "drive_folder_id": "",
                        "cloud_provider": "google_drive",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    imported = import_profiles(target)

    assert save_folder.is_dir()
    assert imported.created_directory_count == 1
    assert imported.unresolved_path_count == 0


def test_import_profiles_can_skip_save_folder_side_effects(tmp_path: Path) -> None:
    target = tmp_path / "profiles.json"
    save_folder = tmp_path / "existing_parent" / "save.v2"
    save_folder.parent.mkdir()
    target.write_text(
        json.dumps(
            {
                "profiles": [
                    {
                        "id": "skip-side-effects",
                        "display_name": "Folder Game",
                        "game_exe_path": "C:/Games/Game.exe",
                        "save_folder_path": str(save_folder),
                        "game_process_names": ["Game.exe"],
                        "drive_filename": "folder_save",
                        "drive_folder_id": "",
                        "cloud_provider": "google_drive",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    imported = import_profiles(target, apply_save_folder_side_effects=False)

    assert imported.profiles[0].save_folder_path == str(save_folder)
    assert imported.created_directory_count == 0
    assert imported.unresolved_path_count == 0
    assert not save_folder.exists()

    created_directory_count, unresolved_path_count = prepare_imported_save_folders(
        imported.profiles
    )

    assert created_directory_count == 1
    assert unresolved_path_count == 0
    assert save_folder.is_dir()


def test_import_leaves_path_unprepared_when_parent_directory_is_missing(tmp_path: Path) -> None:
    target = tmp_path / "profiles.json"
    save_folder = tmp_path / "missing_parent" / "save"
    target.write_text(
        json.dumps(
            {
                "profiles": [
                    {
                        "id": "missing-parent",
                        "display_name": "Folder Game",
                        "game_exe_path": "C:/Games/Game.exe",
                        "save_folder_path": str(save_folder),
                        "game_process_names": ["Game.exe"],
                        "drive_filename": "folder_save",
                        "drive_folder_id": "",
                        "cloud_provider": "google_drive",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    imported = import_profiles(target)

    assert not save_folder.exists()
    assert imported.created_directory_count == 0
    assert imported.unresolved_path_count == 1


def test_import_does_not_create_directory_when_parent_is_a_file(tmp_path: Path) -> None:
    target = tmp_path / "profiles.json"
    parent_file = tmp_path / "existing_parent"
    parent_file.write_text("not a directory", encoding="utf-8")
    save_folder = parent_file / "save"
    target.write_text(
        json.dumps(
            {
                "profiles": [
                    {
                        "id": "parent-is-file",
                        "display_name": "Folder Game",
                        "game_exe_path": "C:/Games/Game.exe",
                        "save_folder_path": str(save_folder),
                        "game_process_names": ["Game.exe"],
                        "drive_filename": "folder_save",
                        "drive_folder_id": "",
                        "cloud_provider": "google_drive",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    imported = import_profiles(target)

    assert not save_folder.exists()
    assert imported.created_directory_count == 0
    assert imported.unresolved_path_count == 1


def test_import_rejects_existing_profile_ids_before_creating_directories(tmp_path: Path) -> None:
    target = tmp_path / "profiles.json"
    save_folder = tmp_path / "existing_parent" / "save"
    save_folder.parent.mkdir()
    target.write_text(
        json.dumps(
            {
                "profiles": [
                    {
                        "id": "conflict-id",
                        "display_name": "Folder Game",
                        "game_exe_path": "C:/Games/Game.exe",
                        "save_folder_path": str(save_folder),
                        "game_process_names": ["Game.exe"],
                        "drive_filename": "folder_save",
                        "drive_folder_id": "",
                        "cloud_provider": "google_drive",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValidationError, match="existiert bereits"):
        import_profiles(target, existing_profile_ids={"conflict-id"})

    assert not save_folder.exists()

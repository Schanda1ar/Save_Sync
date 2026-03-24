import json
from pathlib import Path

from backend.models import AppConfig, GameProfile
from backend.storage import ConfigStore


def test_loads_legacy_config_when_json_missing(tmp_path: Path) -> None:
    legacy = tmp_path / "config.ini"
    legacy.write_text(
        "\n".join(
            [
                "[paths]",
                "save_file=C:/Saves/game.sav",
                "game_exe=C:/Games/Game.exe",
                "drive_filename=game.sav",
                "drive_folder_id=folder123",
                "game_process_names=Game.exe,Launcher.exe",
            ]
        ),
        encoding="utf-8",
    )
    store = ConfigStore(config_path=tmp_path / "profiles.json", base_dir=tmp_path)

    config = store.load()

    assert len(config.profiles) == 1
    assert config.profiles[0].drive_folder_id == "folder123"
    assert config.profiles[0].game_process_names == ["Game.exe", "Launcher.exe"]


def test_save_writes_json_config(tmp_path: Path) -> None:
    store = ConfigStore(config_path=tmp_path / "profiles.json", base_dir=tmp_path)
    profile = GameProfile.create(
        profile_id="profile-1",
        display_name="Example Game",
        game_exe_path="C:/Games/Game.exe",
        save_file_path="C:/Saves/save_dir",
        game_process_names=["Game.exe"],
        drive_filename="save.zip",
        drive_folder_id="folder123",
    )
    config = AppConfig(profiles=[profile], selected_profile_id=profile.id)
    store.save(config)

    payload = json.loads((tmp_path / "profiles.json").read_text(encoding="utf-8"))
    assert payload["selected_profile_id"] == "profile-1"
    assert payload["profiles"][0]["id"] == "profile-1"

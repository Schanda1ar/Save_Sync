import json
from pathlib import Path

from backend.models import AppConfig, GameProfile
from backend.storage import ConfigStore


def test_load_returns_empty_config_when_json_missing(tmp_path: Path) -> None:
    store = ConfigStore(config_path=tmp_path / "profiles.json")

    config = store.load()

    assert config == AppConfig()
    assert config.profiles == []
    assert config.selected_profile_id == ""
    assert not (tmp_path / "profiles.json").exists()


def test_save_writes_json_config(tmp_path: Path) -> None:
    store = ConfigStore(config_path=tmp_path / "profiles.json")
    profile = GameProfile.create(
        profile_id="profile-1",
        display_name="Example Game",
        game_exe_path="C:/Games/Game.exe",
        save_folder_path="C:/Saves/save_dir",
        game_process_names=["Game.exe"],
        drive_filename="save",
        drive_folder_id="folder123",
    )
    config = AppConfig(profiles=[profile], selected_profile_id=profile.id)
    store.save(config)

    payload = json.loads((tmp_path / "profiles.json").read_text(encoding="utf-8"))
    assert payload["selected_profile_id"] == "profile-1"
    assert payload["profiles"][0]["id"] == "profile-1"
    assert payload["profiles"][0]["save_folder_path"] == str(Path("C:/Saves/save_dir"))
    assert payload["profiles"][0]["drive_filename"] == "save.zip"

from pathlib import Path

from backend.models import AppConfig
from backend.ui import AppController
import backend.ui as ui_module


class DummyStore:
    def __init__(self, *args, **kwargs) -> None:
        self.config = AppConfig()

    def load(self) -> AppConfig:
        return self.config

    def save(self, config: AppConfig) -> None:
        self.config = config


def test_controller_exposes_darkmode_as_default(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(ui_module, "ConfigStore", DummyStore)

    controller = AppController(tmp_path)

    assert controller.darkMode is True
    assert controller.selectedProfileData["save_folder_path"] == ""


def test_controller_hides_zip_suffix_in_selected_profile(monkeypatch, tmp_path: Path) -> None:
    store = DummyStore()
    store.config = AppConfig.from_dict(
        {
            "selected_profile_id": "profile-1",
            "profiles": [
                {
                    "id": "profile-1",
                    "display_name": "Example Game",
                    "game_exe_path": "C:/Games/Game.exe",
                    "save_folder_path": "C:/Saves/Game",
                    "game_process_names": ["Game.exe"],
                    "drive_filename": "savegame.zip",
                    "drive_folder_id": "",
                    "cloud_provider": "google_drive",
                }
            ],
        }
    )

    monkeypatch.setattr(ui_module, "ConfigStore", lambda *args, **kwargs: store)

    controller = AppController(tmp_path)

    assert controller.selectedProfileData["drive_filename"] == "savegame"

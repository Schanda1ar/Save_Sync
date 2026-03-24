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


def test_controller_duplicates_selected_profile(monkeypatch, tmp_path: Path) -> None:
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
                    "drive_folder_id": "folder-123",
                    "cloud_provider": "google_drive",
                }
            ],
        }
    )
    monkeypatch.setattr(ui_module, "ConfigStore", lambda *args, **kwargs: store)

    controller = AppController(tmp_path)
    controller.duplicateSelectedProfile()

    assert len(store.config.profiles) == 2
    original = store.config.profiles[0]
    copy_profile = store.config.profiles[1]
    assert copy_profile.id != original.id
    assert copy_profile.display_name == "Example Game (Kopie)"
    assert copy_profile.game_exe_path == original.game_exe_path
    assert copy_profile.save_folder_path == original.save_folder_path
    assert copy_profile.game_process_names == original.game_process_names
    assert copy_profile.drive_filename == original.drive_filename
    assert copy_profile.drive_folder_id == original.drive_folder_id
    assert store.config.selected_profile_id == copy_profile.id
    assert controller.selectedProfileData["display_name"] == "Example Game (Kopie)"
    assert controller.statusMessage == "Profil 'Example Game' als 'Example Game (Kopie)' kopiert."


def test_controller_duplicate_profile_increments_copy_suffix(monkeypatch, tmp_path: Path) -> None:
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
                },
                {
                    "id": "profile-2",
                    "display_name": "Example Game (Kopie)",
                    "game_exe_path": "C:/Games/Game.exe",
                    "save_folder_path": "C:/Saves/Game",
                    "game_process_names": ["Game.exe"],
                    "drive_filename": "savegame-2.zip",
                    "drive_folder_id": "",
                    "cloud_provider": "google_drive",
                },
            ],
        }
    )
    monkeypatch.setattr(ui_module, "ConfigStore", lambda *args, **kwargs: store)

    controller = AppController(tmp_path)
    controller.duplicateSelectedProfile()

    assert store.config.profiles[-1].display_name == "Example Game (Kopie 2)"


def test_controller_duplicate_profile_requires_selection(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(ui_module, "ConfigStore", DummyStore)

    controller = AppController(tmp_path)
    controller.duplicateSelectedProfile()

    assert controller.statusMessage == "Kein Profil ausgewählt."

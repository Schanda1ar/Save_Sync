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


class ImmediateThread:
    def __init__(self, target=None, daemon=None) -> None:
        self._target = target

    def start(self) -> None:
        if self._target is not None:
            self._target()


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


def test_controller_preserves_numeric_steam_id_in_selected_profile(monkeypatch, tmp_path: Path) -> None:
    store = DummyStore()
    store.config = AppConfig.from_dict(
        {
            "selected_profile_id": "profile-1",
            "profiles": [
                {
                    "id": "profile-1",
                    "display_name": "Steam Game",
                    "game_exe_path": "2646460",
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

    assert controller.selectedProfileData["game_exe_path"] == "2646460"


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


def test_controller_save_profile_persists_and_selects_new_profile(
    monkeypatch, tmp_path: Path
) -> None:
    store = DummyStore()
    monkeypatch.setattr(ui_module, "ConfigStore", lambda *args, **kwargs: store)

    controller = AppController(tmp_path)
    controller.saveProfile(
        "",
        "Steam Game",
        "2646460",
        "C:/Saves/Game",
        "Game.exe",
        "steam_backup",
        "folder-42",
    )

    assert len(store.config.profiles) == 1
    assert store.config.profiles[0].display_name == "Steam Game"
    assert store.config.profiles[0].game_exe_path == "2646460"
    assert store.config.selected_profile_id == store.config.profiles[0].id
    assert controller.statusMessage == "Profil 'Steam Game' gespeichert."


def test_controller_select_profile_index_persists_selection_without_profiles_changed(
    monkeypatch, tmp_path: Path
) -> None:
    store = DummyStore()
    store.config = AppConfig.from_dict(
        {
            "selected_profile_id": "profile-1",
            "profiles": [
                {
                    "id": "profile-1",
                    "display_name": "Example Game",
                    "game_exe_path": "2646460",
                    "save_folder_path": "C:/Saves/Game",
                    "game_process_names": ["Game.exe"],
                    "drive_filename": "savegame.zip",
                    "drive_folder_id": "",
                    "cloud_provider": "google_drive",
                },
                {
                    "id": "profile-2",
                    "display_name": "Second Game",
                    "game_exe_path": "2646461",
                    "save_folder_path": "C:/Saves/Game2",
                    "game_process_names": ["Game2.exe"],
                    "drive_filename": "savegame-2.zip",
                    "drive_folder_id": "",
                    "cloud_provider": "google_drive",
                },
            ],
        }
    )
    monkeypatch.setattr(ui_module, "ConfigStore", lambda *args, **kwargs: store)

    controller = AppController(tmp_path)
    profiles_changed = []
    selected_id_changed = []
    selected_data_changed = []
    controller.profilesChanged.connect(lambda: profiles_changed.append(True))
    controller.selectedProfileIdChanged.connect(lambda: selected_id_changed.append(True))
    controller.selectedProfileDataChanged.connect(lambda: selected_data_changed.append(True))

    controller.selectProfileIndex(1)

    assert store.config.selected_profile_id == "profile-2"
    assert profiles_changed == []
    assert len(selected_id_changed) == 1
    assert len(selected_data_changed) == 1
    assert controller.selectedProfileData["display_name"] == "Second Game"


def test_controller_clear_selection_persists_without_profiles_changed(
    monkeypatch, tmp_path: Path
) -> None:
    store = DummyStore()
    store.config = AppConfig.from_dict(
        {
            "selected_profile_id": "profile-1",
            "profiles": [
                {
                    "id": "profile-1",
                    "display_name": "Example Game",
                    "game_exe_path": "2646460",
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
    profiles_changed = []
    selected_id_changed = []
    selected_data_changed = []
    controller.profilesChanged.connect(lambda: profiles_changed.append(True))
    controller.selectedProfileIdChanged.connect(lambda: selected_id_changed.append(True))
    controller.selectedProfileDataChanged.connect(lambda: selected_data_changed.append(True))

    controller.clearSelection()

    assert store.config.selected_profile_id == ""
    assert profiles_changed == []
    assert len(selected_id_changed) == 1
    assert len(selected_data_changed) == 1
    assert controller.selectedProfileData["display_name"] == ""


def test_controller_import_profiles_updates_state(monkeypatch, tmp_path: Path) -> None:
    store = DummyStore()
    monkeypatch.setattr(ui_module, "ConfigStore", lambda *args, **kwargs: store)
    import_file = tmp_path / "import.json"
    import_file.write_text(
        """
        {
          "profiles": [
            {
              "id": "imported",
              "display_name": "Imported Game",
              "game_exe_path": "2646460",
              "save_folder_path": "C:/Saves/Game",
              "game_process_names": ["Game.exe"],
              "drive_filename": "imported_save",
              "drive_folder_id": "folder-99",
              "cloud_provider": "google_drive"
            }
          ]
        }
        """.strip(),
        encoding="utf-8",
    )

    controller = AppController(tmp_path)
    controller.importProfiles(str(import_file))

    assert len(store.config.profiles) == 1
    assert store.config.profiles[0].id == "imported"
    assert controller.statusMessage == "1 Profil(e) importiert."


def test_controller_export_profiles_writes_json(monkeypatch, tmp_path: Path) -> None:
    store = DummyStore()
    store.config = AppConfig.from_dict(
        {
            "selected_profile_id": "profile-1",
            "profiles": [
                {
                    "id": "profile-1",
                    "display_name": "Example Game",
                    "game_exe_path": "2646460",
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
    export_file = tmp_path / "export.json"

    controller = AppController(tmp_path)
    controller.exportProfiles(str(export_file))

    payload = export_file.read_text(encoding="utf-8")
    assert '"id": "profile-1"' in payload
    assert controller.statusMessage == f"Profile exportiert nach {export_file}."


def test_controller_has_no_unsaved_changes_for_selected_profile(monkeypatch, tmp_path: Path) -> None:
    store = DummyStore()
    store.config = AppConfig.from_dict(
        {
            "selected_profile_id": "profile-1",
            "profiles": [
                {
                    "id": "profile-1",
                    "display_name": "Example Game",
                    "game_exe_path": "2646460",
                    "save_folder_path": "C:/Saves/Game",
                    "game_process_names": ["Game.exe", "Launcher.exe"],
                    "drive_filename": "savegame.zip",
                    "drive_folder_id": "folder-123",
                    "cloud_provider": "google_drive",
                }
            ],
        }
    )
    monkeypatch.setattr(ui_module, "ConfigStore", lambda *args, **kwargs: store)

    controller = AppController(tmp_path)

    assert (
        controller.hasUnsavedProfileChanges(
            "Example Game",
            "2646460",
            "C:/Saves/Game",
            "Game.exe, Launcher.exe",
            "savegame",
            "folder-123",
        )
        is False
    )


def test_controller_detects_unsaved_changes_for_selected_profile(monkeypatch, tmp_path: Path) -> None:
    store = DummyStore()
    store.config = AppConfig.from_dict(
        {
            "selected_profile_id": "profile-1",
            "profiles": [
                {
                    "id": "profile-1",
                    "display_name": "Example Game",
                    "game_exe_path": "2646460",
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

    assert (
        controller.hasUnsavedProfileChanges(
            "Example Game geändert",
            "2646460",
            "C:/Saves/Game",
            "Game.exe",
            "savegame",
            "",
        )
        is True
    )


def test_controller_detects_unsaved_changes_for_new_profile_draft(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(ui_module, "ConfigStore", DummyStore)

    controller = AppController(tmp_path)

    assert (
        controller.hasUnsavedProfileChanges(
            "New Game",
            "",
            "",
            "",
            "",
            "",
        )
        is True
    )


def test_controller_start_selected_game_reports_sync_error(monkeypatch, tmp_path: Path) -> None:
    store = DummyStore()
    store.config = AppConfig.from_dict(
        {
            "selected_profile_id": "profile-1",
            "profiles": [
                {
                    "id": "profile-1",
                    "display_name": "Example Game",
                    "game_exe_path": "2646460",
                    "save_folder_path": "C:/Saves/Game",
                    "game_process_names": ["Game.exe"],
                    "drive_filename": "savegame.zip",
                    "drive_folder_id": "",
                    "cloud_provider": "google_drive",
                }
            ],
        }
    )

    class FailingSyncService:
        def __init__(self, *args, **kwargs) -> None:
            pass

        def run_profile(self, profile, status) -> None:
            raise ui_module.SyncError("Drive upload failed")

    monkeypatch.setattr(ui_module, "ConfigStore", lambda *args, **kwargs: store)
    monkeypatch.setattr(ui_module, "SaveSyncService", FailingSyncService)
    monkeypatch.setattr(ui_module.threading, "Thread", ImmediateThread)

    controller = AppController(tmp_path)
    controller.startSelectedGame()

    assert controller.statusMessage == "Fehler: Drive upload failed"
    assert controller.busy is False


def test_controller_start_selected_game_runs_service(monkeypatch, tmp_path: Path) -> None:
    store = DummyStore()
    store.config = AppConfig.from_dict(
        {
            "selected_profile_id": "profile-1",
            "profiles": [
                {
                    "id": "profile-1",
                    "display_name": "Example Game",
                    "game_exe_path": "2646460",
                    "save_folder_path": "C:/Saves/Game",
                    "game_process_names": ["Game.exe"],
                    "drive_filename": "savegame.zip",
                    "drive_folder_id": "",
                    "cloud_provider": "google_drive",
                }
            ],
        }
    )
    calls: list[str] = []

    class RecordingSyncService:
        def __init__(self, *args, **kwargs) -> None:
            pass

        def run_profile(self, profile, status) -> None:
            calls.append(profile.id)
            status("Abgeschlossen")

    monkeypatch.setattr(ui_module, "ConfigStore", lambda *args, **kwargs: store)
    monkeypatch.setattr(ui_module, "SaveSyncService", RecordingSyncService)
    monkeypatch.setattr(ui_module.threading, "Thread", ImmediateThread)

    controller = AppController(tmp_path)
    controller.startSelectedGame()

    assert calls == ["profile-1"]
    assert controller.statusMessage == "Abgeschlossen"
    assert controller.busy is False

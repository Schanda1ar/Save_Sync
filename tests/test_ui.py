from pathlib import Path

from PySide6.QtCore import QUrl

from backend.exchange import ImportProfilesResult
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


def test_controller_save_folder_dialog_start_folder_uses_existing_directory(
    monkeypatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(ui_module, "ConfigStore", DummyStore)
    existing_folder = tmp_path / "save"
    existing_folder.mkdir()

    controller = AppController(tmp_path)

    assert controller.saveFolderDialogStartFolder(str(existing_folder)) == QUrl.fromLocalFile(
        str(existing_folder)
    ).toString()


def test_controller_save_folder_dialog_start_folder_uses_parent_for_existing_file(
    monkeypatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(ui_module, "ConfigStore", DummyStore)
    existing_folder = tmp_path / "save"
    existing_folder.mkdir()
    save_file = existing_folder / "slot1.sav"
    save_file.write_text("data", encoding="utf-8")

    controller = AppController(tmp_path)

    assert controller.saveFolderDialogStartFolder(str(save_file)) == QUrl.fromLocalFile(
        str(existing_folder)
    ).toString()


def test_controller_save_folder_dialog_start_folder_falls_back_to_last_existing_parent(
    monkeypatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(ui_module, "ConfigStore", DummyStore)
    existing_root = tmp_path / "userdata"
    existing_root.mkdir()
    missing_path = existing_root / "123456789" / "1245620" / "remote" / "profile"

    controller = AppController(tmp_path)

    assert controller.saveFolderDialogStartFolder(str(missing_path)) == QUrl.fromLocalFile(
        str(existing_root)
    ).toString()


def test_controller_save_folder_dialog_start_folder_returns_empty_for_blank_path(
    monkeypatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(ui_module, "ConfigStore", DummyStore)

    controller = AppController(tmp_path)

    assert controller.saveFolderDialogStartFolder("   ") == ""


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
    imported_profile = AppConfig.from_dict(
        {
            "profiles": [
                {
                    "id": "imported",
                    "display_name": "Imported Game",
                    "game_exe_path": "2646460",
                    "save_folder_path": str(tmp_path / "save"),
                    "game_process_names": ["Game.exe"],
                    "drive_filename": "imported_save",
                    "drive_folder_id": "folder-99",
                    "cloud_provider": "google_drive",
                }
            ]
        }
    ).profiles[0]
    monkeypatch.setattr(
        ui_module,
        "import_profiles",
        lambda source, existing_profile_ids=None: ImportProfilesResult(
            profiles=[imported_profile],
            rewritten_path_count=1,
            created_directory_count=1,
            unresolved_path_count=0,
        ),
    )

    controller = AppController(tmp_path)
    controller.importProfiles(str(tmp_path / "import.json"))

    assert len(store.config.profiles) == 1
    assert store.config.profiles[0].id == "imported"
    assert controller.statusMessage == "1 Profil(e) importiert. 1 Pfad(e) angepasst. 1 Ordner erstellt."


def test_controller_import_profiles_reports_unresolved_paths(
    monkeypatch, tmp_path: Path
) -> None:
    store = DummyStore()
    monkeypatch.setattr(ui_module, "ConfigStore", lambda *args, **kwargs: store)
    imported_profile = AppConfig.from_dict(
        {
            "profiles": [
                {
                    "id": "imported",
                    "display_name": "Imported Game",
                    "game_exe_path": "2646460",
                    "save_folder_path": str(tmp_path / "missing-parent" / "save"),
                    "game_process_names": ["Game.exe"],
                    "drive_filename": "imported_save",
                    "drive_folder_id": "folder-99",
                    "cloud_provider": "google_drive",
                }
            ]
        }
    ).profiles[0]
    monkeypatch.setattr(
        ui_module,
        "import_profiles",
        lambda source, existing_profile_ids=None: ImportProfilesResult(
            profiles=[imported_profile],
            rewritten_path_count=1,
            created_directory_count=0,
            unresolved_path_count=1,
        ),
    )

    controller = AppController(tmp_path)
    controller.importProfiles(str(tmp_path / "import.json"))

    assert len(store.config.profiles) == 1
    assert controller.statusMessage == (
        "1 Profil(e) importiert. 1 Pfad(e) angepasst. "
        "1 Pfad(e) konnten lokal nicht vorbereitet werden."
    )


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


def test_controller_exposes_recovery_backups_for_selected_profile(
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
                    "save_folder_path": str(tmp_path / "save"),
                    "game_process_names": ["Game.exe"],
                    "drive_filename": "savegame.zip",
                    "drive_folder_id": "",
                    "cloud_provider": "google_drive",
                }
            ],
        }
    )
    oldest = tmp_path / "save_backup_1710000000"
    newest = tmp_path / "save_backup_1720000000"
    oldest.mkdir()
    newest.mkdir()
    (tmp_path / "save_backup_invalid").mkdir()
    sync_service = ui_module.SaveSyncService(base_dir=tmp_path)
    sync_service._write_backup_marker(oldest, profile_id="profile-1", save_folder_name="save", timestamp=1710000000)
    sync_service._write_backup_marker(newest, profile_id="profile-1", save_folder_name="save", timestamp=1720000000)

    monkeypatch.setattr(ui_module, "ConfigStore", lambda *args, **kwargs: store)

    controller = AppController(tmp_path)

    assert controller.recoveryBackups == [
        {
            "label": "save_backup_1720000000",
            "path": str(tmp_path / "save_backup_1720000000"),
        },
        {
            "label": "save_backup_1710000000",
            "path": str(tmp_path / "save_backup_1710000000"),
        },
    ]


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

        def recover_profile_from_backup(self, profile, selected_backup, status) -> None:
            raise AssertionError("recover_profile_from_backup should not be used for start flow")

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
            status("Drive-Download wird vorbereitet")
            status("Synchronisierung abgeschlossen")

        def recover_profile_from_backup(self, profile, selected_backup, status) -> None:
            raise AssertionError("recover_profile_from_backup should not be used for start flow")

    monkeypatch.setattr(ui_module, "ConfigStore", lambda *args, **kwargs: store)
    monkeypatch.setattr(ui_module, "SaveSyncService", RecordingSyncService)
    monkeypatch.setattr(ui_module.threading, "Thread", ImmediateThread)

    controller = AppController(tmp_path)
    controller.startSelectedGame()

    assert calls == ["profile-1"]
    assert controller.statusMessage == "Synchronisierung abgeschlossen"
    assert controller.busy is False


def test_controller_manual_sync_reports_sync_error(monkeypatch, tmp_path: Path) -> None:
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
            raise AssertionError("run_profile should not be used for manual sync")

        def sync_profile(self, profile, status) -> None:
            raise ui_module.SyncError("Manual sync failed")

        def recover_profile_from_backup(self, profile, selected_backup, status) -> None:
            raise AssertionError("recover_profile_from_backup should not be used for manual sync")

    monkeypatch.setattr(ui_module, "ConfigStore", lambda *args, **kwargs: store)
    monkeypatch.setattr(ui_module, "SaveSyncService", FailingSyncService)
    monkeypatch.setattr(ui_module.threading, "Thread", ImmediateThread)

    controller = AppController(tmp_path)
    controller.syncSelectedProfile()

    assert controller.statusMessage == "Fehler: Manual sync failed"
    assert controller.busy is False


def test_controller_manual_sync_runs_service(monkeypatch, tmp_path: Path) -> None:
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
            raise AssertionError("run_profile should not be used for manual sync")

        def sync_profile(self, profile, status) -> None:
            calls.append(profile.id)
            status("Synchronisierung abgeschlossen")

        def recover_profile_from_backup(self, profile, selected_backup, status) -> None:
            raise AssertionError("recover_profile_from_backup should not be used for manual sync")

    monkeypatch.setattr(ui_module, "ConfigStore", lambda *args, **kwargs: store)
    monkeypatch.setattr(ui_module, "SaveSyncService", RecordingSyncService)
    monkeypatch.setattr(ui_module.threading, "Thread", ImmediateThread)

    controller = AppController(tmp_path)
    controller.syncSelectedProfile()

    assert calls == ["profile-1"]
    assert controller.statusMessage == "Synchronisierung abgeschlossen"
    assert controller.busy is False


def test_controller_manual_sync_refreshes_recovery_backups_after_new_backup(
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
                    "save_folder_path": str(tmp_path / "save"),
                    "game_process_names": ["Game.exe"],
                    "drive_filename": "savegame.zip",
                    "drive_folder_id": "",
                    "cloud_provider": "google_drive",
                }
            ],
        }
    )
    backup_path = tmp_path / "save_backup_1720000000"
    state = {"created": False}

    class RecordingSyncService:
        def __init__(self, *args, **kwargs) -> None:
            pass

        def list_recovery_backups(self, profile) -> list[Path]:
            return [backup_path] if state["created"] else []

        def run_profile(self, profile, status) -> None:
            raise AssertionError("run_profile should not be used for manual sync")

        def sync_profile(self, profile, status) -> None:
            state["created"] = True
            status("Synchronisierung abgeschlossen")

        def recover_profile_from_backup(self, profile, selected_backup, status) -> None:
            raise AssertionError("recover_profile_from_backup should not be used for manual sync")

    monkeypatch.setattr(ui_module, "ConfigStore", lambda *args, **kwargs: store)
    monkeypatch.setattr(ui_module, "SaveSyncService", RecordingSyncService)
    monkeypatch.setattr(ui_module.threading, "Thread", ImmediateThread)

    controller = AppController(tmp_path)
    assert controller.recoveryBackups == []

    controller.syncSelectedProfile()

    assert controller.recoveryBackups == [{"label": backup_path.name, "path": str(backup_path)}]


def test_controller_start_selected_game_refreshes_recovery_backups_after_new_backup(
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
                    "save_folder_path": str(tmp_path / "save"),
                    "game_process_names": ["Game.exe"],
                    "drive_filename": "savegame.zip",
                    "drive_folder_id": "",
                    "cloud_provider": "google_drive",
                }
            ],
        }
    )
    backup_path = tmp_path / "save_backup_1720000000"
    state = {"created": False}

    class RecordingSyncService:
        def __init__(self, *args, **kwargs) -> None:
            pass

        def list_recovery_backups(self, profile) -> list[Path]:
            return [backup_path] if state["created"] else []

        def run_profile(self, profile, status) -> None:
            state["created"] = True
            status("Synchronisierung abgeschlossen")

        def recover_profile_from_backup(self, profile, selected_backup, status) -> None:
            raise AssertionError("recover_profile_from_backup should not be used for start flow")

    monkeypatch.setattr(ui_module, "ConfigStore", lambda *args, **kwargs: store)
    monkeypatch.setattr(ui_module, "SaveSyncService", RecordingSyncService)
    monkeypatch.setattr(ui_module.threading, "Thread", ImmediateThread)

    controller = AppController(tmp_path)
    assert controller.recoveryBackups == []

    controller.startSelectedGame()

    assert controller.recoveryBackups == [{"label": backup_path.name, "path": str(backup_path)}]


def test_controller_manual_recovery_requires_backup_selection(
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
    controller.recoverSelectedProfileFromBackup("")

    assert controller.statusMessage == "Kein Backup ausgewählt."


def test_controller_manual_recovery_runs_recovery_service(
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
    backup_path = tmp_path / "save_backup_1720000000"
    calls: list[tuple[str, str]] = []

    class RecordingSyncService:
        def __init__(self, *args, **kwargs) -> None:
            pass

        def list_recovery_backups(self, profile) -> list[Path]:
            return [backup_path]

        def run_profile(self, profile, status) -> None:
            raise AssertionError("run_profile should not be used for manual recovery")

        def sync_profile(self, profile, status) -> None:
            raise AssertionError("sync_profile should not be used for manual recovery")

        def recover_profile_from_backup(self, profile, selected_backup, status) -> None:
            calls.append((profile.id, selected_backup))
            status("Synchronisierung abgeschlossen")

    monkeypatch.setattr(ui_module, "ConfigStore", lambda *args, **kwargs: store)
    monkeypatch.setattr(ui_module, "SaveSyncService", RecordingSyncService)
    monkeypatch.setattr(ui_module.threading, "Thread", ImmediateThread)

    controller = AppController(tmp_path)
    controller.recoverSelectedProfileFromBackup(str(backup_path))

    assert controller.recoveryBackups == [
        {"label": backup_path.name, "path": str(backup_path)}
    ]
    assert calls == [("profile-1", str(backup_path))]
    assert controller.statusMessage == "Synchronisierung abgeschlossen"
    assert controller.busy is False

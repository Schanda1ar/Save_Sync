from __future__ import annotations

import threading
from pathlib import Path
from urllib.parse import unquote, urlparse

from PySide6.QtCore import QObject, Property, Signal, Slot

from .exchange import export_profiles, import_profiles
from .models import (
    AppConfig,
    GameProfile,
    ValidationError,
    normalize_drive_filename,
    normalize_launch_target,
    normalize_process_names,
    normalize_save_folder_path,
)
from .storage import ConfigStore
from .sync import SaveSyncService, SyncError


class AppController(QObject):
    """Expose profile management and sync actions to the QML frontend."""

    profilesChanged = Signal()
    selectedProfileDataChanged = Signal()
    selectedProfileIdChanged = Signal()
    recoveryBackupsChanged = Signal()
    statusMessageChanged = Signal()
    busyChanged = Signal()
    statusUpdateRequested = Signal(str)
    busyUpdateRequested = Signal(bool)
    recoveryBackupsRefreshRequested = Signal()

    def __init__(self, base_dir: Path) -> None:
        super().__init__()
        self._store = ConfigStore(base_dir=base_dir)
        self._sync_service = SaveSyncService(base_dir=base_dir)
        self._status_message = "Bereit"
        self._busy = False
        self._recovery_backups: list[dict[str, str]] = []
        self.statusUpdateRequested.connect(self._apply_status)
        self.busyUpdateRequested.connect(self._apply_busy)
        self.recoveryBackupsRefreshRequested.connect(self._refresh_recovery_backups)
        self._config = self._safe_load()
        self._refresh_recovery_backups()

    def _safe_load(self) -> AppConfig:
        """Load persisted config and recover with an empty config on fatal errors."""
        try:
            config = self._store.load()
        except Exception as exc:
            self._status_message = f"Konfiguration konnte nicht geladen werden: {exc}"
            return AppConfig()
        if not config.selected_profile_id and config.profiles:
            config.selected_profile_id = config.profiles[0].id
        return config

    @Property("QVariantList", notify=profilesChanged)
    def profileOptions(self):
        return [
            {"id": profile.id, "display_name": profile.display_name}
            for profile in self._config.profiles
        ]

    @Property("QVariantMap", notify=selectedProfileDataChanged)
    def selectedProfileData(self):
        profile = self._config.get_profile(self._config.selected_profile_id)
        if profile is None:
            return {
                "id": "",
                "display_name": "",
                "game_exe_path": "",
                "save_folder_path": "",
                "game_process_names": "",
                "drive_filename": "",
                "drive_folder_id": "",
                "cloud_provider": "google_drive",
            }
        data = profile.to_dict()
        data["game_process_names"] = ", ".join(profile.game_process_names)
        data["drive_filename"] = self._display_drive_filename(profile.drive_filename)
        return data

    @Property(str, notify=selectedProfileIdChanged)
    def selectedProfileId(self) -> str:
        return self._config.selected_profile_id

    @Property("QVariantList", notify=recoveryBackupsChanged)
    def recoveryBackups(self):
        """Expose discovered SaveSync backup directories for the selected profile."""
        return self._recovery_backups

    @Property(str, notify=statusMessageChanged)
    def statusMessage(self) -> str:
        return self._status_message

    @Property(bool, notify=busyChanged)
    def busy(self) -> bool:
        return self._busy

    @Property(bool, constant=True)
    def darkMode(self) -> bool:
        return True

    @Slot(int)
    def selectProfileIndex(self, index: int) -> None:
        if index < 0 or index >= len(self._config.profiles):
            self._config.selected_profile_id = ""
        else:
            self._config.selected_profile_id = self._config.profiles[index].id
        self._persist_selection()

    @Slot()
    def clearSelection(self) -> None:
        self._config.selected_profile_id = ""
        self._persist_selection()

    @Slot(str, str, str, str, str, str, str)
    def saveProfile(
        self,
        profile_id: str,
        display_name: str,
        game_exe_path: str,
        save_folder_path: str,
        process_names: str,
        drive_filename: str,
        drive_folder_id: str,
    ) -> None:
        """Create or update the selected profile from the form fields."""
        try:
            profile = GameProfile.create(
                profile_id=profile_id.strip() or None,
                display_name=display_name,
                game_exe_path=game_exe_path,
                save_folder_path=save_folder_path,
                game_process_names=process_names,
                drive_filename=drive_filename,
                drive_folder_id=drive_folder_id,
            )
        except ValidationError as exc:
            self._set_status(str(exc))
            return

        existing = self._config.get_profile(profile.id)
        if existing is None:
            self._config.profiles.append(profile)
        else:
            index = self._config.profiles.index(existing)
            self._config.profiles[index] = profile

        self._config.selected_profile_id = profile.id
        self._persist()
        self._set_status(f"Profil '{profile.display_name}' gespeichert.")

    @Slot()
    def deleteSelectedProfile(self) -> None:
        profile = self._config.get_profile(self._config.selected_profile_id)
        if profile is None:
            self._set_status("Kein Profil ausgewählt.")
            return

        self._config.profiles = [item for item in self._config.profiles if item.id != profile.id]
        self._config.selected_profile_id = self._config.profiles[0].id if self._config.profiles else ""
        self._persist()
        self._set_status(f"Profil '{profile.display_name}' gelöscht.")

    @Slot(str)
    def importProfiles(self, source_url: str) -> None:
        """Import profiles from JSON and reject duplicate profile IDs."""
        path = self._file_url_to_path(source_url)
        if not path:
            self._set_status("Kein Importpfad ausgewählt.")
            return
        try:
            imported = import_profiles(Path(path))
        except (OSError, ValidationError) as exc:
            self._set_status(f"Import fehlgeschlagen: {exc}")
            return

        existing_ids = {profile.id for profile in self._config.profiles}
        for profile in imported:
            if profile.id in existing_ids:
                self._set_status(f"Import fehlgeschlagen: Profil-ID '{profile.id}' existiert bereits.")
                return

        self._config.profiles.extend(imported)
        if not self._config.selected_profile_id and self._config.profiles:
            self._config.selected_profile_id = self._config.profiles[0].id
        self._persist()
        self._set_status(f"{len(imported)} Profil(e) importiert.")

    @Slot(str)
    def exportProfiles(self, target_url: str) -> None:
        """Export all current profiles to the chosen JSON file."""
        path = self._file_url_to_path(target_url)
        if not path:
            self._set_status("Kein Exportpfad ausgewählt.")
            return
        try:
            export_profiles(self._config.profiles, Path(path))
        except OSError as exc:
            self._set_status(f"Export fehlgeschlagen: {exc}")
            return
        self._set_status(f"Profile exportiert nach {path}.")

    @Slot()
    def duplicateSelectedProfile(self) -> None:
        profile = self._config.get_profile(self._config.selected_profile_id)
        if profile is None:
            self._set_status("Kein Profil ausgewählt.")
            return

        copy_profile = GameProfile.create(
            display_name=self._next_copy_name(profile.display_name),
            game_exe_path=profile.game_exe_path,
            save_folder_path=profile.save_folder_path,
            game_process_names=profile.game_process_names,
            drive_filename=profile.drive_filename,
            drive_folder_id=profile.drive_folder_id,
        )
        self._config.profiles.append(copy_profile)
        self._config.selected_profile_id = copy_profile.id
        self._persist()
        self._set_status(
            f"Profil '{profile.display_name}' als '{copy_profile.display_name}' kopiert."
        )

    @Slot()
    def startSelectedGame(self) -> None:
        """Run the sync lifecycle for the selected profile on a background thread."""
        self._run_selected_profile_action(
            action=self._sync_service.run_profile,
            missing_selection_message="Kein Spiel ausgewählt.",
            busy_message="Synchronisierung läuft bereits.",
        )

    @Slot()
    def syncSelectedProfile(self) -> None:
        """Run a manual sync for the selected profile on a background thread."""
        self._run_selected_profile_action(
            action=self._sync_service.sync_profile,
            missing_selection_message="Kein Profil ausgewählt.",
            busy_message="Synchronisierung läuft bereits.",
        )

    @Slot(str)
    def recoverSelectedProfileFromBackup(self, backup_path: str) -> None:
        """Restore a selected local backup and upload it as the new manual truth."""
        if not backup_path.strip():
            self._set_status("Kein Backup ausgewählt.")
            return
        self._run_selected_profile_action(
            action=lambda profile, status: self._sync_service.recover_profile_from_backup(
                profile, backup_path, status
            ),
            missing_selection_message="Kein Profil ausgewählt.",
            busy_message="Synchronisierung läuft bereits.",
        )

    def _run_selected_profile_action(
        self,
        *,
        action,
        missing_selection_message: str,
        busy_message: str,
    ) -> None:
        profile = self._config.get_profile(self._config.selected_profile_id)
        if profile is None:
            self._set_status(missing_selection_message)
            return
        if self._busy:
            self._set_status(busy_message)
            return

        self._set_busy(True)

        def worker() -> None:
            # The sync workflow can block on I/O and process waits, so it must stay off the UI thread.
            try:
                action(profile, self.statusUpdateRequested.emit)
            except (SyncError, ValidationError, OSError, Exception) as exc:
                self.statusUpdateRequested.emit(f"Fehler: {exc}")
            finally:
                # Any sync lifecycle can create a new local backup, so always refresh the list.
                self.recoveryBackupsRefreshRequested.emit()
                self.busyUpdateRequested.emit(False)

        threading.Thread(target=worker, daemon=True).start()

    @Slot(str, str, str, str, str, str, result=bool)
    def hasUnsavedProfileChanges(
        self,
        display_name: str,
        game_exe_path: str,
        save_folder_path: str,
        process_names: str,
        drive_filename: str,
        drive_folder_id: str,
    ) -> bool:
        """Compare the normalized form values with the stored profile state."""
        current_data = {
            "display_name": self._normalized_or_stripped(display_name),
            "game_exe_path": self._normalized_or_stripped(
                game_exe_path, normalize_launch_target
            ),
            "save_folder_path": self._normalized_or_stripped(
                save_folder_path, normalize_save_folder_path
            ),
            "game_process_names": self._normalized_process_names(process_names),
            "drive_filename": self._normalized_display_drive_filename(drive_filename),
            "drive_folder_id": self._normalized_or_stripped(drive_folder_id),
        }

        profile = self._config.get_profile(self._config.selected_profile_id)
        if profile is None:
            return any(
                value if not isinstance(value, list) else len(value) > 0
                for value in current_data.values()
            )

        stored_data = {
            "display_name": profile.display_name,
            "game_exe_path": profile.game_exe_path,
            "save_folder_path": profile.save_folder_path,
            "game_process_names": profile.game_process_names,
            "drive_filename": self._display_drive_filename(profile.drive_filename),
            "drive_folder_id": profile.drive_folder_id,
        }
        return current_data != stored_data

    @Slot(str, result=str)
    def fileUrlToPath(self, source_url: str) -> str:
        return self._file_url_to_path(source_url)

    def _persist(self) -> None:
        self._store.save(self._config)
        self.profilesChanged.emit()
        self.selectedProfileIdChanged.emit()
        self.selectedProfileDataChanged.emit()
        self._refresh_recovery_backups()

    def _persist_selection(self) -> None:
        self._store.save(self._config)
        self.selectedProfileIdChanged.emit()
        self.selectedProfileDataChanged.emit()
        self._refresh_recovery_backups()

    def _set_status(self, message: str) -> None:
        self._apply_status(message)

    @Slot(str)
    def _apply_status(self, message: str) -> None:
        self._status_message = message
        self.statusMessageChanged.emit()

    def _set_busy(self, value: bool) -> None:
        self._apply_busy(value)

    @Slot(bool)
    def _apply_busy(self, value: bool) -> None:
        self._busy = value
        self.busyChanged.emit()

    @Slot()
    def _refresh_recovery_backups(self) -> None:
        """Rescan local SaveSync backups for the currently selected profile."""
        self._recovery_backups = self._load_recovery_backups()
        self.recoveryBackupsChanged.emit()

    def _load_recovery_backups(self) -> list[dict[str, str]]:
        """Safely ask the sync service for current recovery candidates."""
        profile = self._config.get_profile(self._config.selected_profile_id)
        if profile is None:
            return []

        list_backups = getattr(self._sync_service, "list_recovery_backups", None)
        if list_backups is None:
            return []

        try:
            backups = list_backups(profile)
        except Exception:
            # Backup discovery should never break the main profile screen.
            return []

        return [{"label": path.name, "path": str(path)} for path in backups]

    def _file_url_to_path(self, source_url: str) -> str:
        """Convert file URLs from QML dialogs into a local filesystem path."""
        if not source_url:
            return ""
        if "://" not in source_url:
            return source_url
        parsed = urlparse(source_url)
        return unquote(parsed.path.lstrip("/"))

    def _display_drive_filename(self, filename: str) -> str:
        if filename.lower().endswith(".zip"):
            return filename[:-4]
        return filename

    def _normalized_or_stripped(self, value: str, normalizer=None) -> str:
        if normalizer is None:
            return value.strip()
        try:
            return normalizer(value)
        except ValidationError:
            return value.strip()

    def _normalized_process_names(self, value: str) -> list[str]:
        try:
            return normalize_process_names(value)
        except ValidationError:
            return [item.strip() for item in value.split(",") if item.strip()]

    def _normalized_display_drive_filename(self, value: str) -> str:
        try:
            return self._display_drive_filename(normalize_drive_filename(value))
        except ValidationError:
            return value.strip()

    def _next_copy_name(self, base_name: str) -> str:
        existing_names = {profile.display_name for profile in self._config.profiles}
        copy_name = f"{base_name} (Kopie)"
        if copy_name not in existing_names:
            return copy_name

        counter = 2
        while True:
            copy_name = f"{base_name} (Kopie {counter})"
            if copy_name not in existing_names:
                return copy_name
            counter += 1

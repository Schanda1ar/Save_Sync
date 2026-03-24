from __future__ import annotations

import threading
from pathlib import Path
from urllib.parse import unquote, urlparse

from PySide6.QtCore import QObject, Property, QSettings, Signal, Slot

from .exchange import export_profiles, import_profiles
from .models import AppConfig, GameProfile, ValidationError
from .storage import ConfigStore
from .sync import SaveSyncService, SyncError


class AppController(QObject):
    profilesChanged = Signal()
    selectedProfileDataChanged = Signal()
    selectedProfileIdChanged = Signal()
    statusMessageChanged = Signal()
    busyChanged = Signal()
    statusUpdateRequested = Signal(str)
    busyUpdateRequested = Signal(bool)
    themeChanged = Signal()

    def __init__(self, base_dir: Path) -> None:
        super().__init__()
        self._store = ConfigStore(base_dir=base_dir)
        self._sync_service = SaveSyncService(base_dir=base_dir)
        self._status_message = "Bereit"
        self._busy = False
        self._settings = QSettings()
        self._dark_mode = self._settings.value("ui/dark_mode", False, type=bool)
        self.statusUpdateRequested.connect(self._apply_status)
        self.busyUpdateRequested.connect(self._apply_busy)
        self._config = self._safe_load()

    def _safe_load(self) -> AppConfig:
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
                "save_file_path": "",
                "game_process_names": "",
                "drive_filename": "",
                "drive_folder_id": "",
                "cloud_provider": "google_drive",
            }
        data = profile.to_dict()
        data["game_process_names"] = ", ".join(profile.game_process_names)
        return data

    @Property(str, notify=selectedProfileIdChanged)
    def selectedProfileId(self) -> str:
        return self._config.selected_profile_id

    @Property(str, notify=statusMessageChanged)
    def statusMessage(self) -> str:
        return self._status_message

    @Property(bool, notify=busyChanged)
    def busy(self) -> bool:
        return self._busy

    @Property(bool, notify=themeChanged)
    def darkMode(self) -> bool:
        return self._dark_mode

    @Slot(int)
    def selectProfileIndex(self, index: int) -> None:
        if index < 0 or index >= len(self._config.profiles):
            self._config.selected_profile_id = ""
        else:
            self._config.selected_profile_id = self._config.profiles[index].id
        self._persist()

    @Slot()
    def clearSelection(self) -> None:
        self._config.selected_profile_id = ""
        self._persist()

    @Slot()
    def toggleTheme(self) -> None:
        self.setDarkMode(not self._dark_mode)

    @Slot(bool)
    def setDarkMode(self, enabled: bool) -> None:
        if self._dark_mode == enabled:
            return
        self._dark_mode = enabled
        self._settings.setValue("ui/dark_mode", self._dark_mode)
        self._settings.sync()
        self.themeChanged.emit()

    @Slot(str, str, str, str, str, str, str)
    def saveProfile(
        self,
        profile_id: str,
        display_name: str,
        game_exe_path: str,
        save_file_path: str,
        process_names: str,
        drive_filename: str,
        drive_folder_id: str,
    ) -> None:
        try:
            profile = GameProfile.create(
                profile_id=profile_id.strip() or None,
                display_name=display_name,
                game_exe_path=game_exe_path,
                save_file_path=save_file_path,
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
    def startSelectedGame(self) -> None:
        profile = self._config.get_profile(self._config.selected_profile_id)
        if profile is None:
            self._set_status("Kein Spiel ausgewählt.")
            return
        if self._busy:
            self._set_status("Synchronisierung läuft bereits.")
            return

        self._set_busy(True)

        def worker() -> None:
            try:
                self._sync_service.run_profile(profile, self.statusUpdateRequested.emit)
            except (SyncError, ValidationError, OSError, Exception) as exc:
                self.statusUpdateRequested.emit(f"Fehler: {exc}")
            finally:
                self.busyUpdateRequested.emit(False)

        threading.Thread(target=worker, daemon=True).start()

    @Slot(str, result=str)
    def fileUrlToPath(self, source_url: str) -> str:
        return self._file_url_to_path(source_url)

    def _persist(self) -> None:
        self._store.save(self._config)
        self.profilesChanged.emit()
        self.selectedProfileIdChanged.emit()
        self.selectedProfileDataChanged.emit()

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

    def _file_url_to_path(self, source_url: str) -> str:
        if not source_url:
            return ""
        if "://" not in source_url:
            return source_url
        parsed = urlparse(source_url)
        return unquote(parsed.path.lstrip("/"))

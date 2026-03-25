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
    profilesChanged = Signal()
    selectedProfileDataChanged = Signal()
    selectedProfileIdChanged = Signal()
    statusMessageChanged = Signal()
    busyChanged = Signal()
    statusUpdateRequested = Signal(str)
    busyUpdateRequested = Signal(bool)

    def __init__(self, base_dir: Path) -> None:
        super().__init__()
        self._store = ConfigStore(base_dir=base_dir)
        self._sync_service = SaveSyncService(base_dir=base_dir)
        self._status_message = "Bereit"
        self._busy = False
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

    def _persist_selection(self) -> None:
        self._store.save(self._config)
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

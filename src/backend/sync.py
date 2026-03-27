from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import tempfile
import time
import zipfile
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Callable, Iterator

import psutil

from .google_drive import GoogleDriveClient
from .models import GameProfile, is_steam_game_id

StatusCallback = Callable[[str], None]
GAME_LAUNCH_TIMEOUT_SECONDS = 30
HASH_CHUNK_SIZE = 1024 * 1024
RECOVERY_COPY_TIMESTAMP_FORMAT = "%Y%m%d_%H%M%S"
BACKUP_MARKER_FILENAME = "savesync.backup.json"


class SyncError(RuntimeError):
    """Raised when sync or launch workflow fails."""


def calc_hash(path: Path) -> str | None:
    """Return the SHA-256 hash for a file, or ``None`` when it is missing."""
    if not path.exists() or not path.is_file():
        return None
    digest = hashlib.sha256()
    buffer = bytearray(HASH_CHUNK_SIZE)
    view = memoryview(buffer)
    with path.open("rb") as handle:
        while True:
            size = handle.readinto(buffer)
            if not size:
                break
            digest.update(view[:size])
    return digest.hexdigest()


def build_directory_manifest(path: Path) -> dict[str, str]:
    """Map relative file paths to hashes so directory snapshots stay comparable."""
    if not path.exists():
        return {}
    if not path.is_dir():
        raise SyncError(f"Save-Ordner ist ungültig: {path}")

    manifest: dict[str, str] = {}
    for file_path in sorted(item for item in path.rglob("*") if item.is_file()):
        manifest[file_path.relative_to(path).as_posix()] = calc_hash(file_path) or ""
    return manifest


def manifest_digest(manifest: dict[str, str]) -> str:
    """Collapse a manifest into a stable digest for cheap change detection."""
    payload = json.dumps(manifest, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def snapshot_path(path: Path) -> str | None:
    """Return a content digest for a directory, or ``None`` when it does not exist."""
    if not path.exists():
        return None
    return manifest_digest(build_directory_manifest(path))


def save_meta(meta_info: dict[str, str], path: Path) -> None:
    """Persist sync metadata next to the save folder for later inspection."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(meta_info, ensure_ascii=False, indent=2), encoding="utf-8")


class SaveSyncService:
    """Coordinate cloud download, game launch, and upload for one profile."""

    def __init__(self, *, base_dir: Path | None = None) -> None:
        self.drive_client = GoogleDriveClient(base_dir=base_dir)

    def run_profile(self, profile: GameProfile, status: StatusCallback | None = None) -> None:
        """Sync a profile before launch, wait for the game to finish, then sync back."""
        report = status or (lambda _: None)
        save_folder, meta_path = self._prepare_profile(profile, require_launch_target=True)

        report("Authentifizierung läuft")
        drive = self.drive_client.build_drive()

        report("Download läuft")
        initial_hash, cloud_hash, remote_file = self._download_if_needed(drive, profile, save_folder)

        report("Spielstart")
        process = self._launch_game(profile)
        self._wait_for_game(profile, process, report)

        report("Upload läuft")
        final_hash = snapshot_path(save_folder)
        self._upload_if_needed(
            drive,
            profile,
            save_folder,
            meta_path,
            initial_hash,
            final_hash,
            cloud_hash,
            remote_file,
        )
        report("Abgeschlossen")

    def sync_profile(self, profile: GameProfile, status: StatusCallback | None = None) -> None:
        """Sync a profile without launching the game."""
        report = status or (lambda _: None)
        save_folder, meta_path = self._prepare_profile(profile, require_launch_target=False)

        report("Authentifizierung läuft")
        drive = self.drive_client.build_drive()

        report("Download läuft")
        initial_hash, cloud_hash, remote_file = self._download_if_needed(drive, profile, save_folder)

        report("Upload läuft")
        final_hash = snapshot_path(save_folder)
        self._upload_if_needed(
            drive,
            profile,
            save_folder,
            meta_path,
            initial_hash,
            final_hash,
            cloud_hash,
            remote_file,
        )
        report("Abgeschlossen")

    def list_recovery_backups(self, profile: GameProfile) -> list[Path]:
        """Return discovered timestamped local backups for the selected profile."""
        save_folder, _ = self._prepare_profile(profile, require_launch_target=False)
        return self._find_recovery_backups(save_folder, profile.id)

    def recover_profile_from_backup(
        self,
        profile: GameProfile,
        backup_path: str | Path,
        status: StatusCallback | None = None,
    ) -> None:
        """Restore one local backup and force-upload that state back to Google Drive."""
        report = status or (lambda _: None)
        save_folder, meta_path = self._prepare_profile(profile, require_launch_target=False)
        backup_folder = self._validate_recovery_backup(save_folder, Path(backup_path), profile.id)

        report("Authentifizierung läuft")
        drive = self.drive_client.build_drive()

        report("Drive-Archiv wird gesucht")
        remote_file = self._find_remote_file(drive, profile)
        if remote_file is not None:
            report("Drive-Sicherheitskopie wird erstellt")
            self._create_remote_recovery_copy(remote_file, profile)

        report("Backup wird wiederhergestellt")
        # Recovery intentionally restores the selected backup directly into the live save folder.
        self._replace_directory(save_folder, backup_folder)

        report("Upload läuft")
        final_hash = snapshot_path(save_folder)
        if final_hash is None:
            raise SyncError(f"Save-Ordner nicht gefunden: {save_folder}")
        drive_file = self._prepare_drive_file(drive, profile, remote_file)
        self._upload_directory(drive_file, save_folder)
        save_meta({"hash": final_hash, "kind": "directory"}, meta_path)
        report("Abgeschlossen")

    def _meta_path(self, save_folder: Path) -> Path:
        """Store sync metadata next to the configured save directory."""
        return save_folder.parent / f"{save_folder.name}.meta.json"

    def _prepare_profile(
        self, profile: GameProfile, *, require_launch_target: bool
    ) -> tuple[Path, Path]:
        save_folder = Path(profile.save_folder_path)
        meta_path = self._meta_path(save_folder)

        if require_launch_target and not self._is_steam_target(profile.game_exe_path):
            game_exe = Path(profile.game_exe_path)
            if not game_exe.exists():
                raise SyncError(f"Spiel-Executable nicht gefunden: {game_exe}")
        if save_folder.exists() and not save_folder.is_dir():
            raise SyncError(f"Save-Ordner ist ungültig: {save_folder}")
        return save_folder, meta_path

    def _query(self, profile: GameProfile) -> str:
        """Build the Google Drive query for one configured archive filename."""
        filename = profile.drive_filename.replace("'", "\\'")
        if profile.drive_folder_id:
            return (
                f"'{profile.drive_folder_id}' in parents and title='{filename}' and trashed=false"
            )
        return f"title='{filename}' and trashed=false"

    def _find_remote_file(self, drive, profile: GameProfile):
        """Return the first matching Google Drive archive for the profile, if any."""
        file_list = drive.ListFile({"q": self._query(profile)}).GetList()
        return file_list[0] if file_list else None

    def _download_if_needed(self, drive, profile: GameProfile, save_folder: Path):
        """Download and unpack the remote archive so its contents can be compared locally."""
        remote_file = self._find_remote_file(drive, profile)
        local_hash = snapshot_path(save_folder)
        cloud_hash = None

        if remote_file is not None:
            with self._downloaded_remote_directory(remote_file) as (cloud_hash, extracted_path):
                if cloud_hash != local_hash and self._should_replace_local_save(
                    save_folder, remote_file
                ):
                    # Keep a timestamped backup before the cloud version replaces local saves.
                    self._backup_existing(profile, save_folder)
                    self._replace_directory(save_folder, extracted_path)
                    local_hash = cloud_hash

        return local_hash, cloud_hash, remote_file

    def _upload_if_needed(
        self,
        drive,
        profile: GameProfile,
        save_folder: Path,
        meta_path: Path,
        initial_hash: str | None,
        final_hash: str | None,
        cloud_hash: str | None,
        remote_file,
    ) -> None:
        """Upload the save folder unless nothing changed locally or in the cloud."""
        if final_hash is None:
            raise SyncError(f"Save-Ordner nicht gefunden: {save_folder}")
        if cloud_hash and final_hash == cloud_hash:
            return
        if remote_file is not None and final_hash == initial_hash == cloud_hash:
            return

        drive_file = self._prepare_drive_file(drive, profile, remote_file)
        self._upload_directory(drive_file, save_folder)
        save_meta({"hash": final_hash, "kind": "directory"}, meta_path)

    def _upload_metadata(self, profile: GameProfile) -> dict[str, object]:
        """Build the mutable Drive metadata for the configured archive target."""
        metadata: dict[str, object] = {"title": profile.drive_filename}
        if profile.drive_folder_id:
            metadata["parents"] = [{"id": profile.drive_folder_id}]
        return metadata

    def _prepare_drive_file(self, drive, profile: GameProfile, remote_file):
        """Create or retarget the Drive file object that will receive the archive upload."""
        metadata = self._upload_metadata(profile)
        if remote_file is None:
            return drive.CreateFile(metadata)

        for key, value in metadata.items():
            remote_file[key] = value
        return remote_file

    def _wait_for_game(
        self,
        profile: GameProfile,
        process: subprocess.Popen | None,
        report: StatusCallback,
    ) -> None:
        """Wait until the launched game fully exits before continuing with upload."""
        launched = self._wait_for_game_launch(profile, process)
        if not launched:
            raise SyncError("Spielprozess wurde nach dem Start nicht erkannt.")

        report("Spiel läuft")
        while True:
            process_running = process is not None and process.poll() is None
            game_running = self._any_game_process_running(profile)
            if not process_running and not game_running:
                break
            if game_running:
                time.sleep(2)
                continue
            if not process_running:
                break
            time.sleep(2)

    def _wait_for_game_launch(
        self,
        profile: GameProfile,
        process: subprocess.Popen | None,
    ) -> bool:
        """Treat either the spawned process or a known game process name as a successful launch."""
        deadline = time.monotonic() + GAME_LAUNCH_TIMEOUT_SECONDS
        while time.monotonic() < deadline:
            if self._any_game_process_running(profile):
                return True
            if process is not None and process.poll() is None:
                return True
            time.sleep(1)
        return False

    def _launch_game(self, profile: GameProfile) -> subprocess.Popen | None:
        """Launch the profile target directly or via a Steam URI."""
        target = profile.game_exe_path
        if self._is_steam_target(target):
            self._open_steam_uri(self._steam_uri(target))
            return None
        return subprocess.Popen([target], shell=False)

    def _open_steam_uri(self, uri: str) -> None:
        if hasattr(os, "startfile"):
            os.startfile(uri)
            return
        raise SyncError("Steam-Starts werden auf dieser Plattform nicht unterstützt.")

    def _steam_uri(self, game_id: str) -> str:
        return f"steam://rungameid/{game_id}"

    def _is_steam_target(self, target: str) -> bool:
        return is_steam_game_id(target)

    def _any_game_process_running(self, profile: GameProfile) -> bool:
        names = {name.lower() for name in profile.game_process_names}
        for proc in psutil.process_iter(["name"]):
            try:
                name = (proc.info.get("name") or "").lower()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
            if name in names:
                return True
        return False

    @contextmanager
    def _downloaded_remote_directory(self, remote_file) -> Iterator[tuple[str, Path]]:
        """Yield the extracted cloud archive together with its directory digest."""
        with tempfile.TemporaryDirectory() as temp_dir_name:
            temp_dir = Path(temp_dir_name)
            archive_path = temp_dir / "save_archive.zip"
            extracted_path = temp_dir / "extracted"
            remote_file.GetContentFile(str(archive_path))
            extracted_path.mkdir(parents=True, exist_ok=True)
            with zipfile.ZipFile(archive_path, "r") as archive:
                archive.extractall(extracted_path)
            yield manifest_digest(build_directory_manifest(extracted_path)), extracted_path

    def _should_replace_local_save(self, save_folder: Path, remote_file) -> bool:
        """Prefer the newer side when local and cloud saves differ."""
        if not save_folder.exists():
            return True

        local_mtime = self._latest_tree_mtime(save_folder)
        remote_mtime = self._remote_modified_timestamp(remote_file)
        if local_mtime is None or remote_mtime is None:
            return True
        return remote_mtime > local_mtime

    def _latest_tree_mtime(self, path: Path) -> float | None:
        """Return the newest mtime across a directory tree, including directories for deletions."""
        if not path.exists():
            return None
        latest_mtime = path.stat().st_mtime
        for item in path.rglob("*"):
            latest_mtime = max(latest_mtime, item.stat().st_mtime)
        return latest_mtime

    def _remote_modified_timestamp(self, remote_file) -> float | None:
        """Parse the Google Drive modified timestamp into a comparable epoch value."""
        modified = remote_file.get("modifiedDate")
        if not modified:
            return None
        try:
            return datetime.fromisoformat(modified.replace("Z", "+00:00")).timestamp()
        except ValueError:
            return None

    def _find_recovery_backups(self, save_folder: Path, profile_id: str) -> list[Path]:
        """Scan the save folder parent for SaveSync-authored backups for one profile."""
        backup_root = save_folder.parent
        if not backup_root.exists():
            return []

        prefix = f"{save_folder.name}_backup_"
        backups: list[tuple[int, Path]] = []
        for candidate in backup_root.iterdir():
            if not candidate.is_dir() or not candidate.name.startswith(prefix):
                continue
            marker = self._read_backup_marker(candidate)
            if marker is None:
                continue
            if marker.get("profile_id") != profile_id:
                continue
            if marker.get("save_folder_name") != save_folder.name:
                continue

            timestamp = marker.get("timestamp")
            if not isinstance(timestamp, int):
                continue
            backups.append((timestamp, candidate))

        backups.sort(key=lambda item: item[0], reverse=True)
        return [path for _, path in backups]

    def _validate_recovery_backup(
        self, save_folder: Path, backup_path: Path, profile_id: str
    ) -> Path:
        """Accept recovery only from known SaveSync-authored backups for the active profile."""
        if not backup_path.exists():
            raise SyncError(f"Backup-Ordner nicht gefunden: {backup_path}")
        if not backup_path.is_dir():
            raise SyncError(f"Backup-Ordner ist ungültig: {backup_path}")

        resolved_backup = backup_path.resolve()
        for candidate in self._find_recovery_backups(save_folder, profile_id):
            if candidate.resolve() == resolved_backup:
                return candidate
        raise SyncError(f"Backup-Ordner ist kein bekanntes SaveSync-Backup: {backup_path}")

    def _backup_marker_path(self, backup_path: Path) -> Path:
        """Return the marker file path used to prove SaveSync created the backup."""
        return backup_path / BACKUP_MARKER_FILENAME

    def _write_backup_marker(
        self,
        backup_path: Path,
        *,
        profile_id: str,
        save_folder_name: str,
        timestamp: int,
    ) -> None:
        """Persist enough metadata to identify trusted SaveSync backup directories."""
        marker_payload = {
            "profile_id": profile_id,
            "save_folder_name": save_folder_name,
            "timestamp": timestamp,
        }
        self._backup_marker_path(backup_path).write_text(
            json.dumps(marker_payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _read_backup_marker(self, backup_path: Path) -> dict[str, object] | None:
        """Load the SaveSync backup marker, or ``None`` when the directory is untrusted."""
        marker_path = self._backup_marker_path(backup_path)
        if not marker_path.exists():
            return None
        try:
            payload = json.loads(marker_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        if not isinstance(payload, dict):
            return None
        return payload

    def _create_remote_recovery_copy(self, remote_file, profile: GameProfile) -> None:
        """Preserve the current Drive archive before a manual recovery overwrites it."""
        remote_file.Copy(
            target_folder=self._recovery_target_folder(profile, remote_file),
            new_title=self._recovery_copy_title(profile.drive_filename),
        )

    def _recovery_target_folder(self, profile: GameProfile, remote_file):
        """Prefer the configured Drive folder, otherwise reuse the current file parent."""
        if profile.drive_folder_id:
            return {"id": profile.drive_folder_id}

        parents = remote_file.get("parents") or []
        if not parents:
            return None

        parent_id = parents[0].get("id")
        if not parent_id:
            return None
        return {"id": parent_id}

    def _recovery_copy_title(self, drive_filename: str) -> str:
        """Build a stable timestamped archive name for the pre-recovery Drive copy."""
        timestamp = datetime.now().strftime(RECOVERY_COPY_TIMESTAMP_FORMAT)
        return f"{Path(drive_filename).stem}_pre_recovery_{timestamp}.zip"

    def _upload_directory(self, drive_file, save_folder: Path) -> None:
        """Archive a save directory as ZIP and upload it to the configured Drive file."""
        with tempfile.NamedTemporaryFile(delete=False, suffix=".zip") as temp_file:
            archive_path = Path(temp_file.name)
        try:
            with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
                for file_path in sorted(item for item in save_folder.rglob("*") if item.is_file()):
                    archive.write(file_path, arcname=file_path.relative_to(save_folder).as_posix())
            drive_file["description"] = "savesync:directory"
            drive_file.SetContentFile(str(archive_path))
            drive_file.Upload()
        finally:
            self._release_drive_file_content(drive_file)
            self._cleanup_temp_archive(archive_path)

    def _release_drive_file_content(self, drive_file) -> None:
        content = getattr(drive_file, "content", None)
        if content is None:
            return
        try:
            content.close()
        except OSError:
            pass
        drive_file.content = None

    def _cleanup_temp_archive(self, archive_path: Path) -> None:
        try:
            if archive_path.exists():
                archive_path.unlink()
        except OSError:
            pass

    def _backup_existing(self, profile: GameProfile, save_folder: Path) -> None:
        """Copy the current save folder into a trusted timestamped SaveSync backup directory."""
        if not save_folder.exists():
            return
        if not save_folder.is_dir():
            raise SyncError(f"Save-Ordner ist ungültig: {save_folder}")
        timestamp = int(time.time())
        backup_path = save_folder.parent / f"{save_folder.name}_backup_{timestamp}"
        shutil.copytree(save_folder, backup_path)
        self._write_backup_marker(
            backup_path,
            profile_id=profile.id,
            save_folder_name=save_folder.name,
            timestamp=timestamp,
        )

    def _replace_directory(self, target: Path, source: Path) -> None:
        if target.exists():
            shutil.rmtree(target)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(source, target)

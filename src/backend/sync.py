from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import tempfile
import time
import zipfile
from pathlib import Path
from typing import Callable

import psutil

from .google_drive import GoogleDriveClient
from .models import GameProfile

StatusCallback = Callable[[str], None]


class SyncError(RuntimeError):
    """Raised when sync or launch workflow fails."""


def calc_hash(path: Path) -> str | None:
    if not path.exists() or not path.is_file():
        return None
    with path.open("rb") as handle:
        return hashlib.sha256(handle.read()).hexdigest()


def build_directory_manifest(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    if not path.is_dir():
        raise SyncError(f"Save-Ordner ist ungültig: {path}")

    manifest: dict[str, str] = {}
    for file_path in sorted(item for item in path.rglob("*") if item.is_file()):
        manifest[file_path.relative_to(path).as_posix()] = calc_hash(file_path) or ""
    return manifest


def manifest_digest(manifest: dict[str, str]) -> str:
    payload = json.dumps(manifest, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def snapshot_path(path: Path) -> str | None:
    if not path.exists():
        return None
    return manifest_digest(build_directory_manifest(path))


def save_meta(meta_info: dict[str, str], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(meta_info, ensure_ascii=False, indent=2), encoding="utf-8")


class SaveSyncService:
    def __init__(self, *, base_dir: Path | None = None) -> None:
        self.drive_client = GoogleDriveClient(base_dir=base_dir)

    def run_profile(self, profile: GameProfile, status: StatusCallback | None = None) -> None:
        report = status or (lambda _: None)
        save_folder = Path(profile.save_folder_path)
        game_exe = Path(profile.game_exe_path)
        meta_path = self._meta_path(save_folder)

        if not game_exe.exists():
            raise SyncError(f"Spiel-Executable nicht gefunden: {game_exe}")
        if save_folder.exists() and not save_folder.is_dir():
            raise SyncError(f"Save-Ordner ist ungültig: {save_folder}")

        report("Authentifizierung läuft")
        drive = self.drive_client.build_drive()

        report("Download läuft")
        initial_hash, cloud_hash, remote_file = self._download_if_needed(drive, profile, save_folder)

        report("Spielstart")
        process = subprocess.Popen([str(game_exe)], shell=False)
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

    def _meta_path(self, save_folder: Path) -> Path:
        return save_folder.parent / f"{save_folder.name}.meta.json"

    def _query(self, profile: GameProfile) -> str:
        filename = profile.drive_filename.replace("'", "\\'")
        if profile.drive_folder_id:
            return (
                f"'{profile.drive_folder_id}' in parents and title='{filename}' and trashed=false"
            )
        return f"title='{filename}' and trashed=false"

    def _download_if_needed(self, drive, profile: GameProfile, save_folder: Path):
        file_list = drive.ListFile({"q": self._query(profile)}).GetList()
        remote_file = file_list[0] if file_list else None
        local_hash = snapshot_path(save_folder)
        cloud_hash = None

        if remote_file is not None:
            cloud_hash = self._download_directory_digest(remote_file)

        if cloud_hash and cloud_hash != local_hash:
            self._backup_existing(save_folder)
            self._download_directory(remote_file, save_folder)
            local_hash = snapshot_path(save_folder)

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
        if final_hash is None:
            raise SyncError(f"Save-Ordner nicht gefunden: {save_folder}")
        if final_hash == initial_hash:
            return
        if cloud_hash and final_hash == cloud_hash:
            return

        drive_file = remote_file
        metadata = {"title": profile.drive_filename}
        if profile.drive_folder_id:
            metadata["parents"] = [{"id": profile.drive_folder_id}]

        if drive_file is None:
            drive_file = drive.CreateFile(metadata)

        self._upload_directory(drive_file, save_folder)
        save_meta({"hash": final_hash, "kind": "directory"}, meta_path)

    def _wait_for_game(
        self,
        profile: GameProfile,
        process: subprocess.Popen,
        report: StatusCallback,
    ) -> None:
        report("Spiel läuft")
        time.sleep(3)
        while True:
            if process.poll() is not None and not self._any_game_process_running(profile):
                break
            if self._any_game_process_running(profile):
                time.sleep(2)
                continue
            if process.poll() is not None:
                break
            time.sleep(2)

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

    def _download_directory_digest(self, remote_file) -> str | None:
        with tempfile.TemporaryDirectory() as temp_dir_name:
            temp_dir = Path(temp_dir_name)
            archive_path = temp_dir / "save_archive.zip"
            extracted_path = temp_dir / "extracted"
            remote_file.GetContentFile(str(archive_path))
            extracted_path.mkdir(parents=True, exist_ok=True)
            with zipfile.ZipFile(archive_path, "r") as archive:
                archive.extractall(extracted_path)
            return manifest_digest(build_directory_manifest(extracted_path))

    def _download_directory(self, remote_file, save_folder: Path) -> None:
        with tempfile.TemporaryDirectory() as temp_dir_name:
            temp_dir = Path(temp_dir_name)
            archive_path = temp_dir / "save_archive.zip"
            extracted_path = temp_dir / "extracted"
            remote_file.GetContentFile(str(archive_path))
            extracted_path.mkdir(parents=True, exist_ok=True)
            with zipfile.ZipFile(archive_path, "r") as archive:
                archive.extractall(extracted_path)
            self._replace_directory(save_folder, extracted_path)

    def _upload_directory(self, drive_file, save_folder: Path) -> None:
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
            if archive_path.exists():
                archive_path.unlink()

    def _backup_existing(self, save_folder: Path) -> None:
        if not save_folder.exists():
            return
        if not save_folder.is_dir():
            raise SyncError(f"Save-Ordner ist ungültig: {save_folder}")
        timestamp = int(time.time())
        backup_path = save_folder.parent / f"{save_folder.name}_backup_{timestamp}"
        shutil.copytree(save_folder, backup_path)

    def _replace_directory(self, target: Path, source: Path) -> None:
        if target.exists():
            shutil.rmtree(target)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(source, target)
